#!/usr/bin/env python3
"""
Stage 3: 段階的AI評価システム
論文内容解釈と段階的評価を実装

scoring_byClaude.mdとprompt_byChatgpt.mdの仕様に基づく
"""

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio
import os

# 既存の正規化・文献検索機能を使用
from .medical_normalizer_v2 import MedicalTermNormalizer, NormalizationResult
from .literature_searcher import LiteratureSearcher, SearchResult

@dataclass 
class EvaluationStage:
    """評価段階の結果"""
    stage: str
    input_data: Dict
    output_data: Dict
    processing_time: float
    success: bool
    error_message: Optional[str] = None

@dataclass
class StagedEvaluationResult:
    """段階的評価の最終結果"""
    claim_text: str
    stages: List[EvaluationStage]
    final_score: int
    final_label: str
    confidence: str
    detailed_breakdown: Dict
    audit_log: Dict
    timestamp: str
    
class StagedEvaluator:
    """段階的AI評価システム"""
    
    def __init__(self):
        self.normalizer = MedicalTermNormalizer()
        self.literature_searcher = LiteratureSearcher()
        self.scoring_rubric = self._load_scoring_rubric()
        
    def _load_scoring_rubric(self) -> Dict:
        """スコアリングルーブリックv3.0を読み込み"""
        return {
            "evidence_alignment": {"max": 60, "description": "エビデンス整合性"},
            "citation_quality": {"max": 22, "description": "引用品質"},
            "scope_nuance": {"max": 12, "description": "適切な限定"},
            "quantitative_accuracy": {"max": 6, "description": "量的正確性"},
            "safety_risk_handling": {"max": 6, "description": "安全配慮"},
            "penalties": {"max": -100, "description": "減点項目"},
            "bonus": {"max": 15, "description": "加点項目"}
        }
    
    async def evaluate_staged(self, claim_text: str, language: str = "ja") -> StagedEvaluationResult:
        """段階的評価のメイン処理"""
        stages = []
        timestamp = datetime.now().isoformat()
        
        try:
            # Stage 1: 主張正規化
            stage1 = await self._stage1_normalization(claim_text, language)
            stages.append(stage1)
            
            if not stage1.success:
                return self._create_failed_result(claim_text, stages, "正規化段階でエラー")
            
            # Stage 2: 文献探索
            stage2 = await self._stage2_literature_search(claim_text, stage1.output_data)
            stages.append(stage2)
            
            if not stage2.success:
                return self._create_failed_result(claim_text, stages, "文献検索段階でエラー") 
                
            # Stage 3: 論文内容解釈・総合分析
            stage3 = await self._stage3_paper_interpretation(stage1.output_data, stage2.output_data)
            stages.append(stage3)
            
            # Stage 4: 段階的スコアリング
            stage4 = await self._stage4_staged_scoring(
                claim_text, stage1.output_data, stage2.output_data, stage3.output_data
            )
            stages.append(stage4)
            
            # 最終結果の構築
            final_score = stage4.output_data.get("total_score", 0)
            final_label = stage4.output_data.get("label", "Unknown")
            confidence = stage4.output_data.get("confidence", "low")
            
            return StagedEvaluationResult(
                claim_text=claim_text,
                stages=stages,
                final_score=final_score,
                final_label=final_label,
                confidence=confidence,
                detailed_breakdown=stage4.output_data.get("score_breakdown", {}),
                audit_log=self._create_audit_log(stages),
                timestamp=timestamp
            )
            
        except Exception as e:
            return self._create_failed_result(claim_text, stages, str(e))
    
    async def _stage1_normalization(self, claim_text: str, language: str) -> EvaluationStage:
        """Stage 1: 主張正規化（PICO分析・検索語抽出）"""
        start_time = datetime.now()
        
        try:
            # 正規化実行
            normalized = self.normalizer.normalize_claim(claim_text, language)
            
            # prompt_byChatgpt.mdの1)主張正規化フォーマットに準拠
            output_data = {
                "lang": language,
                "normalized_claim": f"{normalized.search_query}は有効か？",
                "domain_tags": [normalized.medical_field] if normalized.medical_field else [],
                "PICO": {
                    "Population": normalized.population or "",
                    "Intervention_or_Exposure": normalized.intervention or "",
                    "Comparator": "",
                    "Outcomes": [normalized.outcome] if normalized.outcome else [],
                    "Timeframe_or_Setting": ""
                },
                "key_terms_ja": normalized.medical_terms,
                "key_terms_en": normalized.key_concepts,
                "mesh_terms": [],  # MeSH用語は今後実装
                "pubmed_query_candidates": [normalized.search_query],
                "filters": {
                    "species": "Humans",
                    "language": ["English", "Japanese"],
                    "study_design_priority": [
                        "Systematic Review", "Randomized Controlled Trial", 
                        "Prospective Cohort", "Case-Control", "Cross-Sectional"
                    ],
                    "date_window": "last 10 years"
                },
                "api_used": normalized.api_used,
                "confidence": normalized.confidence
            }
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return EvaluationStage(
                stage="normalization",
                input_data={"claim_text": claim_text, "language": language},
                output_data=output_data,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            return EvaluationStage(
                stage="normalization",
                input_data={"claim_text": claim_text, "language": language},
                output_data={},
                processing_time=processing_time,
                success=False,
                error_message=str(e)
            )
    
    async def _stage2_literature_search(self, claim_text: str, normalization_data: Dict) -> EvaluationStage:
        """Stage 2: 高精度文献検索・一次スクリーニング"""
        start_time = datetime.now()
        
        try:
            # 文献検索実行
            search_result = self.literature_searcher.search_literature(claim_text, max_articles=10)
            
            # prompt_byChatgpt.mdの2)文献探索フォーマットに準拠
            included_studies = []
            excluded_studies = []
            
            for article in search_result.articles:
                # 各論文の基本情報を構造化
                study_data = {
                    "pmid": article.pmid,
                    "doi": getattr(article, 'doi', None),
                    "year": article.publication_date.year if article.publication_date else None,
                    "country": getattr(article, 'country', None),
                    "design": article.study_type,
                    "population": self._extract_population(article.abstract),
                    "intervention": self._extract_intervention(article.abstract),
                    "comparator": self._extract_comparator(article.abstract),
                    "primary_outcomes": self._extract_outcomes(article.abstract),
                    "effect_direction": "not_reported",  # 要実装: アブストラクト解析
                    "effect_size": {"measure": None, "value": None, "ci": None, "p": None},
                    "bias_risk": "unclear",  # 要実装: 研究デザイン品質評価
                    "funding_coi": "unknown",
                    "retraction_status": "unknown",  # 要実装: Retraction Watch連携
                    "abstract_150w": article.abstract[:150] + "..." if len(article.abstract) > 150 else article.abstract
                }
                included_studies.append(study_data)
            
            output_data = {
                "lang": "ja",
                "search_log": {
                    "engine": ["PubMed"],
                    "date": datetime.now().isoformat(),
                    "queries": [{"q": q, "hits": len(search_result.articles)} for q in search_result.search_queries],
                    "filters_applied": {
                        "species": "Humans",
                        "years": "2014-2024",
                        "types": ["systematic_review", "randomized_controlled_trial", "cohort"]
                    }
                },
                "screening": {
                    "excluded": excluded_studies
                },
                "included_studies": included_studies,
                "search_summary": search_result.search_summary,
                "total_articles": len(included_studies)
            }
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return EvaluationStage(
                stage="literature_search",
                input_data={"claim_text": claim_text, "normalization": normalization_data},
                output_data=output_data,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            return EvaluationStage(
                stage="literature_search",
                input_data={"claim_text": claim_text, "normalization": normalization_data},
                output_data={},
                processing_time=processing_time,
                success=False,
                error_message=str(e)
            )
    
    async def _stage3_paper_interpretation(self, normalization_data: Dict, search_data: Dict) -> EvaluationStage:
        """Stage 3: 論文内容解釈・エビデンス総合（新機能）"""
        start_time = datetime.now()
        
        try:
            included_studies = search_data.get("included_studies", [])
            
            # 各論文の詳細解釈（AIベース）
            interpreted_papers = []
            for study in included_studies:
                interpretation = await self._interpret_single_paper(study)
                interpreted_papers.append(interpretation)
            
            # エビデンス総合とGRADE評価
            evidence_synthesis = self._synthesize_evidence(interpreted_papers, normalization_data)
            
            # prompt_byChatgpt.mdの3)総合解釈フォーマットに準拠
            output_data = {
                "lang": "ja",
                "evidence_synthesis": evidence_synthesis,
                "alignment_to_claim": self._assess_claim_alignment(evidence_synthesis, normalization_data),
                "interpreted_papers": interpreted_papers,
                "quality_assessment": self._assess_overall_quality(interpreted_papers),
                "heterogeneity_analysis": self._analyze_heterogeneity(interpreted_papers),
                "grade_assessment": evidence_synthesis["GRADE_certainty"]
            }
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return EvaluationStage(
                stage="paper_interpretation",
                input_data={"normalization": normalization_data, "search": search_data},
                output_data=output_data,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            return EvaluationStage(
                stage="paper_interpretation",
                input_data={"normalization": normalization_data, "search": search_data},
                output_data={},
                processing_time=processing_time,
                success=False,
                error_message=str(e)
            )
    
    async def _stage4_staged_scoring(self, claim_text: str, norm_data: Dict, search_data: Dict, interp_data: Dict) -> EvaluationStage:
        """Stage 4: 段階的スコアリング（ルーブリックv3.0準拠）"""
        start_time = datetime.now()
        
        try:
            # scoring_byClaude.mdの詳細ルーブリックに基づくスコアリング
            score_breakdown = {}
            
            # A. Evidence Alignment (最大60点)
            evidence_score = self._score_evidence_alignment(interp_data, norm_data)
            score_breakdown["evidence_alignment"] = evidence_score
            
            # B. Citation Quality (最大22点)
            citation_score = self._score_citation_quality(search_data)
            score_breakdown["citation_quality"] = citation_score
            
            # C. Scope & Nuance (最大12点)  
            scope_score = self._score_scope_nuance(norm_data, interp_data)
            score_breakdown["scope_nuance"] = scope_score
            
            # D. Quantitative Accuracy (最大6点)
            quant_score = self._score_quantitative_accuracy(interp_data)
            score_breakdown["quantitative_accuracy"] = quant_score
            
            # E. Safety Risk Handling (最大6点)
            safety_score = self._score_safety_handling(claim_text, interp_data)
            score_breakdown["safety_risk_handling"] = safety_score
            
            # 減点・加点の評価
            penalties = self._assess_penalties(claim_text, search_data, interp_data)
            bonus = self._assess_bonus(search_data, interp_data)
            
            # 総合スコア計算
            base_score = sum(score_breakdown.values())
            total_score = max(0, min(100, base_score + bonus - penalties))
            
            # ラベル判定（scoring_byClaude.mdの閾値に基づく）
            label = self._determine_label(total_score)
            confidence = self._determine_confidence(total_score, interp_data)
            
            output_data = {
                "lang": "ja",
                "score_breakdown": score_breakdown,
                "penalties": penalties,
                "bonus": bonus,
                "total_score": total_score,
                "label": label,
                "confidence": confidence,
                "public_facing_summary_ja": self._generate_public_summary(
                    claim_text, total_score, label, interp_data
                ),
                "detailed_rationale": self._generate_detailed_rationale(score_breakdown, interp_data)
            }
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return EvaluationStage(
                stage="staged_scoring",
                input_data={
                    "claim": claim_text,
                    "normalization": norm_data,
                    "search": search_data,
                    "interpretation": interp_data
                },
                output_data=output_data,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            return EvaluationStage(
                stage="staged_scoring",
                input_data={},
                output_data={},
                processing_time=processing_time,
                success=False,
                error_message=str(e)
            )
    
    # 詳細解釈・評価メソッド群
    
    async def _interpret_single_paper(self, study: Dict) -> Dict:
        """個別論文の詳細解釈"""
        # AIによる論文内容の深い解釈（今後OpenAI/Geminiを利用）
        # 現在は基本的な情報抽出のみ実装
        return {
            "pmid": study.get("pmid"),
            "title": study.get("title", ""),
            "study_design": study.get("design"),
            "quality_rating": "moderate",  # RoB 2.0評価（要実装）
            "effect_size_interpretation": "moderate_effect",  # 効果量解釈（要実装）
            "clinical_significance": "unclear",  # 臨床的意義（要実装）
            "limitations": [],  # 限界点（要実装）
            "funding_bias_risk": "unknown",  # 資金バイアス（要実装）
            "abstract_summary": study.get("abstract_150w", "")
        }
    
    def _synthesize_evidence(self, papers: List[Dict], norm_data: Dict) -> Dict:
        """エビデンス総合とGRADE評価"""
        if not papers:
            return {
                "statement_ja": "関連する研究が見つかりませんでした。",
                "key_points": ["エビデンス不足"],
                "GRADE_certainty": "very_low"
            }
        
        # 研究デザインの質に基づくGRADE評価
        has_sr = any(p.get("study_design") == "systematic_review" for p in papers)
        has_rct = any(p.get("study_design") == "randomized_controlled_trial" for p in papers)
        
        if has_sr:
            grade = "moderate"
        elif has_rct:
            grade = "moderate"
        elif len(papers) >= 3:
            grade = "low"
        else:
            grade = "very_low"
        
        statement = f"見つかった{len(papers)}件の研究に基づく評価。"
        key_points = [f"研究数: {len(papers)}件", f"主な研究デザイン: {papers[0].get('study_design', 'unknown')}"]
        
        return {
            "statement_ja": statement,
            "key_points": key_points,
            "GRADE_certainty": grade
        }
    
    def _assess_claim_alignment(self, synthesis: Dict, norm_data: Dict) -> str:
        """主張とエビデンスの整合性評価"""
        grade = synthesis.get("GRADE_certainty", "very_low")
        
        # 簡易的な整合性判定（詳細なNLI分析は今後実装）
        if grade in ["high", "moderate"]:
            return "partially_supports"
        elif grade == "low":
            return "neutral"
        else:
            return "insufficient"
    
    def _score_evidence_alignment(self, interp_data: Dict, norm_data: Dict) -> int:
        """A. Evidence Alignment スコアリング（最大60点）"""
        alignment = interp_data.get("alignment_to_claim", "insufficient")
        grade = interp_data.get("evidence_synthesis", {}).get("GRADE_certainty", "very_low")
        
        # scoring_byClaude.mdのA-1マトリクスに基づく
        alignment_scores = {
            "supports": {"high": 58, "moderate": 50, "low": 40, "very_low": 30},
            "partially_supports": {"high": 44, "moderate": 34, "low": 24, "very_low": 14},
            "neutral": {"high": 19, "moderate": 19, "low": 19, "very_low": 19},
            "contradicts": {"high": 5, "moderate": 9, "low": 14, "very_low": 14},
            "insufficient": {"high": 15, "moderate": 15, "low": 15, "very_low": 15}
        }
        
        return alignment_scores.get(alignment, {}).get(grade, 15)
    
    def _score_citation_quality(self, search_data: Dict) -> int:
        """B. Citation Quality スコアリング（最大22点）"""
        included_studies = search_data.get("included_studies", [])
        if not included_studies:
            return 0
        
        # B-1: 検証可能性（最大8点）
        verifiability = 6 if included_studies[0].get("pmid") else 3
        
        # B-2: ソース階層（最大7点）
        study_types = [s.get("design", "") for s in included_studies]
        if "systematic_review" in study_types:
            hierarchy = 7
        elif "randomized_controlled_trial" in study_types:
            hierarchy = 5
        elif any("cohort" in t for t in study_types):
            hierarchy = 4
        else:
            hierarchy = 2
        
        # B-3: 新しさ（最大3点）
        current_year = datetime.now().year
        years = [s.get("year", 2000) for s in included_studies if s.get("year")]
        if years:
            newest_year = max(years)
            if current_year - newest_year <= 5:
                recency = 3
            elif current_year - newest_year <= 10:
                recency = 2
            else:
                recency = 1
        else:
            recency = 1
        
        # B-4: 透明性（最大2点）
        transparency = 1  # 部分的記載（検索ログあり）
        
        # B-5: 利益相反透明性（最大2点）
        coi_transparency = 0  # 未実装
        
        return verifiability + hierarchy + recency + transparency + coi_transparency
    
    def _score_scope_nuance(self, norm_data: Dict, interp_data: Dict) -> int:
        """C. Scope & Nuance スコアリング（最大12点）"""
        # C-1: PICO適合性（最大3点）
        pico = norm_data.get("PICO", {})
        pico_score = 2 if pico.get("Population") and pico.get("Intervention_or_Exposure") else 1
        
        # C-2: 外的妥当性（最大3点）
        # 簡易実装: populationフィールドの存在で判定
        external_validity = 2 if pico.get("Population") else 1
        
        # C-3: 限界の明示（最大3点）
        limitations_score = 1  # 基本的な限界言及（詳細実装要）
        
        # C-4: 因果vs相関の区別（最大3点）
        causation_score = 2  # 適切な表現（詳細実装要）
        
        return pico_score + external_validity + limitations_score + causation_score
    
    def _score_quantitative_accuracy(self, interp_data: Dict) -> int:
        """D. Quantitative Accuracy スコアリング（最大6点）"""
        # 簡易実装: 今後効果量・信頼区間の詳細分析を追加
        return 4  # 基本的な数値情報あり
    
    def _score_safety_handling(self, claim_text: str, interp_data: Dict) -> int:
        """E. Safety Risk Handling スコアリング（最大6点）"""
        # 簡易実装: 今後有害事象・安全性情報の詳細分析を追加
        return 3  # 基本的な安全配慮
    
    def _assess_penalties(self, claim_text: str, search_data: Dict, interp_data: Dict) -> int:
        """減点項目の評価"""
        penalties = 0
        
        # 重大減点項目の確認（要実装）
        # - 撤回論文使用チェック
        # - 捕食ジャーナルチェック
        # - 統計的誤解釈チェック
        
        return penalties
    
    def _assess_bonus(self, search_data: Dict, interp_data: Dict) -> int:
        """加点項目の評価"""
        bonus = 0
        
        # 研究・引用の質による加点
        studies = search_data.get("included_studies", [])
        if len(studies) >= 3:
            bonus += 2  # 複数研究での裏取り
        
        # 情報の完全性による加点
        if interp_data.get("grade_assessment"):
            bonus += 3  # 不確実性の適切な提示
        
        return min(bonus, 15)  # 最大15点
    
    def _determine_label(self, score: int) -> str:
        """スコアに基づくラベル判定"""
        if score >= 85:
            return "True / Mostly True"
        elif score >= 60:
            return "Mixed / Context Needed"
        elif score >= 30:
            return "Unsupported / Misleading"
        else:
            return "False / Harmful"
    
    def _determine_confidence(self, score: int, interp_data: Dict) -> str:
        """信頼度の判定"""
        grade = interp_data.get("grade_assessment", "very_low")
        
        if grade in ["high", "moderate"] and score >= 60:
            return "high"
        elif grade == "low" or score < 30:
            return "low"
        else:
            return "medium"
    
    def _generate_public_summary(self, claim: str, score: int, label: str, interp_data: Dict) -> str:
        """一般向けサマリーの生成"""
        papers_count = len(interp_data.get("interpreted_papers", []))
        grade = interp_data.get("grade_assessment", "very_low")
        
        return f"「{claim}」について、{papers_count}件の医学論文を分析した結果、スコア{score}点（{label}）。エビデンスの確信度は{grade}レベルです。"
    
    def _generate_detailed_rationale(self, score_breakdown: Dict, interp_data: Dict) -> List[Dict]:
        """詳細な根拠の生成"""
        rationales = []
        
        for category, score in score_breakdown.items():
            rationales.append({
                "category": category,
                "score": score,
                "max_score": self.scoring_rubric.get(category, {}).get("max", 100),
                "reasoning": f"{self.scoring_rubric.get(category, {}).get('description', category)}: {score}点"
            })
        
        return rationales
    
    # ヘルパーメソッド群
    
    def _extract_population(self, abstract: str) -> str:
        """アブストラクトから対象集団を抽出"""
        # 簡易実装（今後NLP強化）
        if "patient" in abstract.lower():
            return "patients"
        elif "adult" in abstract.lower():
            return "adults"
        else:
            return "unclear"
    
    def _extract_intervention(self, abstract: str) -> str:
        """アブストラクトから介入を抽出"""
        # 簡易実装（今後NLP強化）
        return "unclear"
    
    def _extract_comparator(self, abstract: str) -> str:
        """アブストラクトから比較対照を抽出"""
        # 簡易実装（今後NLP強化）
        if "placebo" in abstract.lower():
            return "placebo"
        elif "control" in abstract.lower():
            return "control"
        else:
            return "unclear"
    
    def _extract_outcomes(self, abstract: str) -> List[str]:
        """アブストラクトからアウトカムを抽出"""
        # 簡易実装（今後NLP強化）
        return ["unclear"]
    
    def _assess_overall_quality(self, papers: List[Dict]) -> Dict:
        """全体的な研究品質の評価"""
        return {
            "average_quality": "moderate",
            "quality_range": "low-high",
            "bias_risk_summary": "some concerns"
        }
    
    def _analyze_heterogeneity(self, papers: List[Dict]) -> Dict:
        """研究間異質性の分析"""
        return {
            "statistical_heterogeneity": "unknown",
            "clinical_heterogeneity": "moderate",
            "methodological_diversity": "high"
        }
    
    def _create_audit_log(self, stages: List[EvaluationStage]) -> Dict:
        """監査ログの作成"""
        return {
            "timestamp": datetime.now().isoformat(),
            "stages_completed": len([s for s in stages if s.success]),
            "total_processing_time": sum(s.processing_time for s in stages),
            "stage_details": [
                {
                    "stage": s.stage,
                    "success": s.success,
                    "processing_time": s.processing_time,
                    "error": s.error_message
                } for s in stages
            ]
        }
    
    def _create_failed_result(self, claim_text: str, stages: List[EvaluationStage], error_msg: str) -> StagedEvaluationResult:
        """失敗時の結果作成"""
        return StagedEvaluationResult(
            claim_text=claim_text,
            stages=stages,
            final_score=0,
            final_label="Error",
            confidence="low",
            detailed_breakdown={},
            audit_log={"error": error_msg},
            timestamp=datetime.now().isoformat()
        )