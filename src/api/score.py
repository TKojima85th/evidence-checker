from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import time
import asyncio
from src.models.claim import ClaimRequest, ClaimResponse, AxisScore, Rationale, EvidenceItem, ClaimReviewMetadata, ClaimReviewSchema, ErrorResponse, ErrorDetail
from src.database import get_db
from src.config import settings
from src.core.extract import extract_main_claim
from src.utils.pubmed import search_evidence
from src.core.scoring import calculate_evidence_score

router = APIRouter()


async def process_claim_comprehensive(claim_text: str, source_url: str = None) -> dict:
    """
    包括的な主張評価：extract→evidence→scoring の統合処理
    """
    try:
        # Step 1: 主張抽出
        claim_extract = extract_main_claim(claim_text)
        
        # Step 2: エビデンス検索（PubMed）
        evidence_list = search_evidence(claim_text, max_results=5)
        
        # Step 3: 包括的スコア計算
        score_result = calculate_evidence_score(
            claim_dict=claim_extract,
            evidence_list=evidence_list,
            original_text=claim_text,
            source_url=source_url
        )
        
        # 結果の構造化
        axis_scores = {
            "clarity": score_result["scores"].clarity,
            "evidence_quality": score_result["scores"].evidence_quality,
            "consensus": score_result["scores"].consensus,
            "biological_plausibility": score_result["scores"].biological_plausibility,
            "transparency": score_result["scores"].transparency,
            "context_distortion": score_result["scores"].context_distortion,
            "harm_potential": score_result["scores"].harm_potential,
            "virality": score_result["scores"].virality,
            "correction_response": score_result["scores"].correction_response
        }
        
        return {
            "total_score": score_result["total_score"],
            "label": score_result["label"],
            "axis_scores": axis_scores,
            "rationales": score_result["rationales"],
            "evidence_list": evidence_list,
            "extracted_claim": claim_extract
        }
        
    except Exception as e:
        # エラー時はフォールバック（簡易スコア）
        print(f"包括的評価エラー: {e}")
        return await fallback_scoring(claim_text)


async def fallback_scoring(claim_text: str) -> dict:
    """フォールバック用の簡易スコア計算"""
    text_length = len(claim_text)
    
    # 基本的なスコア
    clarity = 3 if text_length > 50 else 2
    evidence_quality = 1  # エビデンス検索失敗
    consensus = 2
    biological_plausibility = 3
    transparency = 1
    context_distortion = 3
    harm_potential = 4
    virality = 2
    correction_response = 0
    
    total = (
        clarity * 10 + evidence_quality * 20 + consensus * 15 +
        biological_plausibility * 10 + transparency * 10 +
        context_distortion * 10 + harm_potential * 15 +
        virality * 5 + correction_response * 5
    ) // 5
    
    label = "Unsupported"  # エラー時は安全側に倒す
    
    return {
        "total_score": total,
        "label": label,
        "axis_scores": {
            "clarity": clarity,
            "evidence_quality": evidence_quality,
            "consensus": consensus,
            "biological_plausibility": biological_plausibility,
            "transparency": transparency,
            "context_distortion": context_distortion,
            "harm_potential": harm_potential,
            "virality": virality,
            "correction_response": correction_response
        },
        "rationales": [
            {
                "axis": "evidence_quality",
                "score": evidence_quality,
                "reasoning": "システムエラーによりエビデンス検索ができませんでした。"
            }
        ],
        "evidence_list": [],
        "extracted_claim": {"text": claim_text, "confidence": 0.1, "type": "general"}
    }


@router.post("/score", response_model=ClaimResponse)
async def evaluate_claim(
    request: ClaimRequest,
    db: Session = Depends(get_db)
):
    """
    主張の信頼性を9軸ルーブリックで評価
    """
    start_time = time.time()
    
    try:
        # 入力検証
        if len(request.claim_text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_INPUT", "message": "主張文が空です"}
            )
        
        if len(request.claim_text) > settings.max_claim_length:
            raise HTTPException(
                status_code=400,
                detail={"code": "CLAIM_TOO_LONG", "message": f"主張文が長すぎます（最大{settings.max_claim_length}文字）"}
            )
        
        # 包括的なスコア計算
        score_result = await process_claim_comprehensive(request.claim_text, request.source_url)
        
        # 処理時間計算
        processing_time = time.time() - start_time
        
        # エビデンスリストの変換（NLI結果を含む）
        evidence_items = []
        analyzed_evidence = score_result.get("analyzed_evidence", score_result.get("evidence_list", []))
        
        for evidence in analyzed_evidence[:3]:
            evidence_items.append(EvidenceItem(
                source=evidence.get("pmid", "不明"),
                title=evidence.get("title", ""),
                stance=evidence.get("stance", "neutral"),  # NLI結果を使用
                relevance_score=evidence.get("stance_confidence", evidence.get("relevance_score", 0.5)),
                summary=evidence.get("abstract", "")[:200] + "..." if len(evidence.get("abstract", "")) > 200 else evidence.get("abstract", "")
            ))
        
        # フォールバック：エビデンスがない場合
        if not evidence_items:
            evidence_items.append(EvidenceItem(
                source="検索結果なし",
                title="関連するエビデンスが見つかりませんでした",
                stance="neutral",
                relevance_score=0.0,
                summary="PubMed検索で関連する研究が見つからなかったか、検索システムエラーが発生しました。"
            ))
        
        # 理由リストの変換
        rationale_items = []
        for rationale in score_result.get("rationales", []):
            rationale_items.append(Rationale(
                axis=rationale.get("axis", "unknown"),
                score=rationale.get("score", 0),
                reasoning=rationale.get("reasoning", "")
            ))
        
        # レスポンス構築
        response = ClaimResponse(
            total_score=score_result["total_score"],
            label=score_result["label"],
            axis_scores=AxisScore(**score_result["axis_scores"]),
            rationales=rationale_items,
            evidence_top3=evidence_items,
            metadata=ClaimReviewMetadata(
                processing_time=processing_time,
                timestamp=datetime.now(),
                model_version="integrated-0.2.0",
                confidence=score_result.get("extracted_claim", {}).get("confidence", 0.5)
            ),
            claim_review=ClaimReviewSchema(
                claimReviewed=request.claim_text,
                reviewRating={
                    "@type": "Rating",
                    "ratingValue": score_result["total_score"],
                    "bestRating": 100,
                    "worstRating": 0,
                    "alternateName": score_result["label"]
                },
                itemReviewed={
                    "@type": "Claim",
                    "text": request.claim_text,
                    "url": request.source_url or ""
                },
                url="http://localhost:8000/api/v1/score",
                datePublished=datetime.now().isoformat(),
                author={
                    "@type": "Organization",
                    "name": "Evidence Checker"
                }
            )
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "INTERNAL_ERROR", "message": f"内部エラーが発生しました: {str(e)}"}
        )