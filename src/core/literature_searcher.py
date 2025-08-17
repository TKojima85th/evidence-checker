"""
Stage 2: 高精度文献検索モジュール

Stage 1の医学用語正規化結果を活用して、PubMed検索を最適化する。
OpenAI APIによる検索クエリ最適化とフィルタリング機能を提供。
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI

from src.config import settings
from src.core.medical_normalizer_v2 import MedicalTermNormalizer, NormalizedClaim
from src.utils.pubmed import PubMedSearcher, PubMedArticle

logger = logging.getLogger(__name__)


@dataclass
class LiteratureSearchResult:
    """文献検索結果データ"""
    original_claim: str
    normalized_claim: NormalizedClaim
    search_queries: List[str]
    articles: List[PubMedArticle]
    search_summary: str
    confidence: float
    api_used: str


@dataclass
class ArticleRelevance:
    """論文関連度評価"""
    article: PubMedArticle
    relevance_score: float
    relevance_reasoning: str
    evidence_strength: str  # "strong", "moderate", "weak", "insufficient"
    supports_claim: Optional[bool]  # True=支持, False=反対, None=不明


class LiteratureSearcher:
    """高精度文献検索クラス"""
    
    def __init__(self, preferred_api: Optional[str] = None):
        """
        初期化
        
        Args:
            preferred_api: 使用するAPI ("openai", "gemini", "deepseek", "fallback")
        """
        self.preferred_api = preferred_api or settings.literature_search_api
        self.normalizer = MedicalTermNormalizer()
        self.pubmed_searcher = PubMedSearcher()
        
        # OpenAI クライアント初期化
        self.openai_client = None
        if settings.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=settings.openai_api_key)
                logger.info("✅ LiteratureSearcher: OpenAI API初期化完了")
            except Exception as e:
                logger.warning(f"❌ LiteratureSearcher: OpenAI API初期化失敗: {e}")
    
    def search_literature(self, claim_text: str, max_articles: int = 10) -> LiteratureSearchResult:
        """
        包括的な文献検索を実行
        
        Args:
            claim_text: 検索対象の主張
            max_articles: 取得する最大論文数
            
        Returns:
            LiteratureSearchResult: 検索結果
        """
        logger.info(f"🔍 文献検索開始: {claim_text[:50]}...")
        
        # Step 1: 医学用語正規化
        normalized = self.normalizer.normalize_claim(claim_text)
        logger.info(f"📋 正規化完了: {normalized.search_query}")
        
        # Step 2: 検索クエリの生成・最適化
        search_queries = self._generate_optimized_queries(normalized)
        logger.info(f"🔧 検索クエリ生成: {len(search_queries)}個")
        
        # Step 3: PubMed検索実行
        all_articles = []
        for query in search_queries:
            articles = self.pubmed_searcher.search_articles(query, max_articles // len(search_queries))
            all_articles.extend(articles)
        
        # 重複除去
        unique_articles = self._remove_duplicates(all_articles)
        logger.info(f"📚 検索結果: {len(unique_articles)}件の論文")
        
        # Step 4: 関連度評価とフィルタリング
        if self.openai_client and len(unique_articles) > 0:
            filtered_articles = self._evaluate_article_relevance(normalized, unique_articles[:max_articles])
        else:
            filtered_articles = unique_articles[:max_articles]
        
        # Step 5: 検索サマリー生成
        search_summary = self._generate_search_summary(normalized, filtered_articles)
        
        confidence = self._calculate_search_confidence(normalized, filtered_articles)
        
        return LiteratureSearchResult(
            original_claim=claim_text,
            normalized_claim=normalized,
            search_queries=search_queries,
            articles=filtered_articles,
            search_summary=search_summary,
            confidence=confidence,
            api_used=normalized.api_used
        )
    
    def _generate_optimized_queries(self, normalized: NormalizedClaim) -> List[str]:
        """正規化結果から最適化された検索クエリを生成"""
        
        if not self.openai_client:
            # フォールバック: 基本的なクエリ生成
            return self._generate_fallback_queries(normalized)
        
        try:
            prompt = f"""
以下の正規化された医学主張について、PubMed検索用の効果的なクエリを3つ生成してください。

正規化結果:
- 医学用語: {', '.join(normalized.medical_terms)}
- 基本クエリ: {normalized.search_query}
- 医学分野: {normalized.medical_field}
- 介入: {normalized.intervention}
- 結果: {normalized.outcome}
- 対象集団: {normalized.population}

以下の観点から多角的なクエリを作成:
1. 直接的な介入-結果関係の研究
2. 系統的レビュー・メタ解析
3. 最新の臨床研究

重要な要求:
- MeSH用語を適切に使用
- 研究の質を向上させるフィルターを含める
- 英語の正確な医学用語を使用
- 各クエリは異なる検索戦略を採用

JSON配列形式で出力:
["query1", "query2", "query3"]
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "PubMed検索の専門家として、効果的な検索戦略を提案してください。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON部分を抽出
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "[" in content and "]" in content:
                start = content.find("[")
                end = content.rfind("]") + 1
                json_str = content[start:end]
            else:
                json_str = content
            
            queries = json.loads(json_str)
            
            if isinstance(queries, list) and len(queries) > 0:
                logger.info(f"✅ OpenAI APIによるクエリ最適化成功: {len(queries)}個")
                return queries
            else:
                raise ValueError("Invalid query format")
                
        except Exception as e:
            logger.warning(f"❌ OpenAI クエリ最適化失敗: {e}")
            return self._generate_fallback_queries(normalized)
    
    def _generate_fallback_queries(self, normalized: NormalizedClaim) -> List[str]:
        """フォールバック: 基本的なクエリ生成"""
        queries = []
        
        # 基本クエリ
        base_query = normalized.search_query
        if base_query:
            queries.append(base_query + " AND humans[MeSH Terms] AND english[Language]")
        
        # 介入+結果のクエリ
        if normalized.intervention and normalized.outcome:
            intervention_outcome = f"{normalized.intervention} AND {normalized.outcome}"
            queries.append(intervention_outcome + " AND (randomized controlled trial[Publication Type] OR meta-analysis[Publication Type])")
        
        # レビュー論文専用クエリ
        if len(normalized.medical_terms) > 0:
            review_query = " ".join(normalized.medical_terms[:3])
            queries.append(review_query + " AND (systematic review[Publication Type] OR meta-analysis[Publication Type])")
        
        return queries[:3] if queries else [normalized.search_query or "medical research"]
    
    def _remove_duplicates(self, articles: List[PubMedArticle]) -> List[PubMedArticle]:
        """重複論文を除去"""
        seen_pmids = set()
        unique_articles = []
        
        for article in articles:
            if article.pmid not in seen_pmids:
                seen_pmids.add(article.pmid)
                unique_articles.append(article)
        
        return unique_articles
    
    def _evaluate_article_relevance(self, normalized: NormalizedClaim, articles: List[PubMedArticle]) -> List[PubMedArticle]:
        """OpenAI APIを使用して論文の関連度を評価"""
        
        if not self.openai_client or not articles:
            return articles
        
        evaluated_articles = []
        
        for article in articles[:10]:  # 最初の10件を評価
            try:
                relevance = self._evaluate_single_article(normalized, article)
                if relevance.relevance_score >= 0.6:  # 関連度60%以上のみ保持
                    evaluated_articles.append(article)
                    logger.debug(f"✅ 論文採用: {article.title[:50]}... (関連度: {relevance.relevance_score:.2f})")
                else:
                    logger.debug(f"❌ 論文除外: {article.title[:50]}... (関連度: {relevance.relevance_score:.2f})")
                    
            except Exception as e:
                logger.warning(f"⚠️ 論文評価エラー: {e}")
                evaluated_articles.append(article)  # エラー時は保持
        
        return evaluated_articles
    
    def _evaluate_single_article(self, normalized: NormalizedClaim, article: PubMedArticle) -> ArticleRelevance:
        """単一論文の関連度を評価"""
        
        prompt = f"""
以下の医学論文が、指定された主張にどの程度関連しているか評価してください。

主張の正規化結果:
- 医学用語: {', '.join(normalized.medical_terms)}
- 検索クエリ: {normalized.search_query}
- 医学分野: {normalized.medical_field}
- 介入: {normalized.intervention}
- 結果: {normalized.outcome}

論文情報:
- タイトル: {article.title}
- アブストラクト: {article.abstract[:800]}
- 研究タイプ: {article.study_type}
- ジャーナル: {article.journal}

以下の形式でJSON評価を出力:
{{
    "relevance_score": 0.0から1.0の数値,
    "relevance_reasoning": "関連度の理由（50文字以内）",
    "evidence_strength": "strong/moderate/weak/insufficient",
    "supports_claim": true/false/null
}}

評価基準:
- 1.0: 主張に直接関連し、高品質な研究
- 0.8: 主張に関連し、信頼できる研究
- 0.6: 部分的に関連、参考になる
- 0.4: 間接的に関連
- 0.2: わずかに関連
- 0.0: 関連なし
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "医学文献の関連度評価の専門家として、客観的で厳格な評価を行ってください。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON抽出
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
            else:
                json_str = content
            
            result = json.loads(json_str)
            
            return ArticleRelevance(
                article=article,
                relevance_score=result.get("relevance_score", 0.5),
                relevance_reasoning=result.get("relevance_reasoning", "評価不可"),
                evidence_strength=result.get("evidence_strength", "insufficient"),
                supports_claim=result.get("supports_claim")
            )
            
        except Exception as e:
            logger.warning(f"論文関連度評価エラー: {e}")
            return ArticleRelevance(
                article=article,
                relevance_score=0.5,  # デフォルト値
                relevance_reasoning="自動評価失敗",
                evidence_strength="insufficient",
                supports_claim=None
            )
    
    def _generate_search_summary(self, normalized: NormalizedClaim, articles: List[PubMedArticle]) -> str:
        """検索結果のサマリーを生成"""
        
        if not articles:
            return f"「{normalized.search_query}」に関する論文が見つかりませんでした。"
        
        # 研究タイプの分布
        study_types = {}
        for article in articles:
            study_type = article.study_type or "other"
            study_types[study_type] = study_types.get(study_type, 0) + 1
        
        # 新しい研究の割合
        recent_count = 0
        if articles[0].publication_date:
            from datetime import datetime
            current_year = datetime.now().year
            for article in articles:
                if article.publication_date and (current_year - article.publication_date.year) <= 5:
                    recent_count += 1
        
        study_type_summary = ", ".join([f"{k}: {v}件" for k, v in study_types.items()])
        
        summary = f"""
検索クエリ「{normalized.search_query}」で{len(articles)}件の関連論文を発見。
研究タイプ: {study_type_summary}。
過去5年以内の研究: {recent_count}件。
"""
        
        return summary.strip()
    
    def _calculate_search_confidence(self, normalized: NormalizedClaim, articles: List[PubMedArticle]) -> float:
        """検索の信頼度を計算"""
        confidence = 0.0
        
        # 正規化の信頼度
        confidence += normalized.confidence * 0.3
        
        # 論文数による評価
        if len(articles) >= 5:
            confidence += 0.3
        elif len(articles) >= 2:
            confidence += 0.2
        elif len(articles) >= 1:
            confidence += 0.1
        
        # 研究の質による評価
        high_quality_count = 0
        for article in articles:
            if article.study_type in ["meta-analysis", "randomized_controlled_trial"]:
                high_quality_count += 1
        
        if high_quality_count >= 2:
            confidence += 0.3
        elif high_quality_count >= 1:
            confidence += 0.2
        
        # API使用による信頼度ボーナス
        if normalized.api_used != "fallback":
            confidence += 0.1
        
        return min(confidence, 0.95)


# グローバルインスタンス
literature_searcher = LiteratureSearcher()