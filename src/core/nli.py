import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import re
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NLIResult:
    """NLI判定結果"""
    stance: str  # "support", "contradict", "neutral"
    confidence: float  # 0.0-1.0
    reasoning: str


class MultilingualNLI:
    """多言語対応のNLI（自然言語推論）クラス"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.nli_model = None
        self.nli_tokenizer = None
        self.sentence_model = None
        self._initialize_models()
    
    def _initialize_models(self):
        """モデルの初期化"""
        try:
            # 多言語NLIモデル（軽量版）
            model_name = "microsoft/DialoGPT-medium"  # フォールバック用
            # 実際には "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli" などを使用
            
            # より軽量なモデルを試す
            try:
                nli_model_name = "cross-encoder/nli-deberta-v3-small"
                self.sentence_model = SentenceTransformer(nli_model_name)
                logger.info(f"NLIモデル '{nli_model_name}' を読み込みました")
            except Exception as e:
                logger.warning(f"高性能NLIモデルの読み込みに失敗: {e}")
                # フォールバック：sentence-transformersの基本モデル
                self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("フォールバック用sentence-transformersモデルを使用")
                
        except Exception as e:
            logger.error(f"モデル初期化エラー: {e}")
            self.sentence_model = None
    
    def analyze_claim_evidence_pair(self, claim: str, evidence: str) -> NLIResult:
        """主張とエビデンスのペアを分析"""
        if not self.sentence_model:
            return self._rule_based_nli(claim, evidence)
        
        try:
            # Sentence-BERT based semantic similarity
            return self._semantic_similarity_nli(claim, evidence)
        except Exception as e:
            logger.warning(f"NLI分析エラー: {e}")
            return self._rule_based_nli(claim, evidence)
    
    def _semantic_similarity_nli(self, claim: str, evidence: str) -> NLIResult:
        """セマンティック類似度ベースのNLI"""
        # テキストの前処理
        claim_clean = self._preprocess_text(claim)
        evidence_clean = self._preprocess_text(evidence)
        
        # エンベディングの計算
        embeddings = self.sentence_model.encode([claim_clean, evidence_clean])
        claim_embedding = embeddings[0]
        evidence_embedding = embeddings[1]
        
        # コサイン類似度の計算
        similarity = np.dot(claim_embedding, evidence_embedding) / (
            np.linalg.norm(claim_embedding) * np.linalg.norm(evidence_embedding)
        )
        
        # 矛盾パターンの検出
        contradiction_score = self._detect_contradiction_patterns(claim, evidence)
        
        # 支持パターンの検出
        support_score = self._detect_support_patterns(claim, evidence)
        
        # 総合判定
        if contradiction_score > 0.7:
            stance = "contradict"
            confidence = contradiction_score
            reasoning = "エビデンスが主張と矛盾する内容を含んでいます。"
        elif support_score > 0.6 and similarity > 0.3:
            stance = "support"
            confidence = min(support_score, similarity + 0.2)
            reasoning = f"エビデンスが主張を支持しています（類似度: {similarity:.2f}）。"
        elif similarity > 0.5:
            stance = "support"
            confidence = similarity
            reasoning = f"エビデンスと主張に高い類似性があります（類似度: {similarity:.2f}）。"
        elif similarity < 0.1:
            stance = "neutral"
            confidence = 0.8 - similarity
            reasoning = "エビデンスと主張の関連性が低いです。"
        else:
            stance = "neutral"
            confidence = 0.5
            reasoning = "エビデンスと主張の関係は中立的です。"
        
        return NLIResult(
            stance=stance,
            confidence=min(1.0, max(0.0, confidence)),
            reasoning=reasoning
        )
    
    def _rule_based_nli(self, claim: str, evidence: str) -> NLIResult:
        """ルールベースのNLI（フォールバック）"""
        # キーワードベースの簡易判定
        claim_keywords = self._extract_keywords(claim)
        evidence_keywords = self._extract_keywords(evidence)
        
        # 共通キーワードの数
        common_keywords = set(claim_keywords) & set(evidence_keywords)
        keyword_overlap = len(common_keywords) / max(len(claim_keywords), 1)
        
        # 矛盾パターン
        contradiction_score = self._detect_contradiction_patterns(claim, evidence)
        
        # 支持パターン
        support_score = self._detect_support_patterns(claim, evidence)
        
        if contradiction_score > 0.7:
            return NLIResult("contradict", contradiction_score, "ルールベース分析により矛盾を検出")
        elif support_score > 0.6:
            return NLIResult("support", support_score, "ルールベース分析により支持を検出")
        elif keyword_overlap > 0.3:
            return NLIResult("support", keyword_overlap, f"キーワード一致率: {keyword_overlap:.2f}")
        else:
            return NLIResult("neutral", 0.5, "関連性が不明確")
    
    def _preprocess_text(self, text: str) -> str:
        """テキストの前処理"""
        # HTMLタグの除去
        text = re.sub(r'<[^>]+>', '', text)
        # 余分な空白の除去
        text = re.sub(r'\s+', ' ', text)
        # 先頭・末尾の空白除去
        text = text.strip()
        return text
    
    def _extract_keywords(self, text: str) -> List[str]:
        """キーワード抽出（簡易版）"""
        # 医学・健康関連の重要語を抽出
        medical_terms = re.findall(
            r'(ビタミン[A-Z]?|ミネラル|サプリメント|薬|治療|効果|副作用|リスク|予防|'
            r'免疫|感染|ウイルス|細菌|がん|癌|心臓病|糖尿病|高血圧|コレステロール|'
            r'血糖値|血圧|健康|医療|医学|診断|検査|ワクチン|接種)', 
            text
        )
        
        # 数値と単位
        numbers = re.findall(r'\d+[%％倍]?', text)
        
        # 一般的なキーワード
        words = re.findall(r'[ぁ-んァ-ヶー一-龯A-Za-z]+', text)
        important_words = [w for w in words if len(w) > 2]
        
        return medical_terms + numbers + important_words[:10]
    
    def _detect_contradiction_patterns(self, claim: str, evidence: str) -> float:
        """矛盾パターンの検出"""
        contradiction_patterns = [
            # 直接的な否定
            (r'効果.*ない', r'効果.*ある', 0.9),
            (r'安全.*でない', r'安全.*である', 0.9),
            (r'リスク.*ない', r'リスク.*ある', 0.8),
            # 相反する数値
            (r'増加', r'減少', 0.7),
            (r'向上', r'悪化', 0.7),
            (r'改善', r'悪化', 0.8),
        ]
        
        max_contradiction = 0.0
        
        for claim_pattern, evidence_pattern, score in contradiction_patterns:
            if re.search(claim_pattern, claim) and re.search(evidence_pattern, evidence):
                max_contradiction = max(max_contradiction, score)
            elif re.search(evidence_pattern, claim) and re.search(claim_pattern, evidence):
                max_contradiction = max(max_contradiction, score)
        
        return max_contradiction
    
    def _detect_support_patterns(self, claim: str, evidence: str) -> float:
        """支持パターンの検出"""
        support_patterns = [
            # 同じ方向性
            (r'効果.*ある', r'効果.*ある', 0.8),
            (r'安全.*である', r'安全.*である', 0.8),
            (r'リスク.*ある', r'リスク.*ある', 0.7),
            (r'改善', r'改善', 0.7),
            (r'向上', r'向上', 0.7),
            (r'増加', r'増加', 0.6),
            (r'減少', r'減少', 0.6),
        ]
        
        max_support = 0.0
        
        for claim_pattern, evidence_pattern, score in support_patterns:
            if re.search(claim_pattern, claim) and re.search(evidence_pattern, evidence):
                max_support = max(max_support, score)
        
        return max_support


class EvidenceStanceAnalyzer:
    """エビデンスの立場分析クラス"""
    
    def __init__(self):
        self.nli = MultilingualNLI()
    
    def analyze_evidence_list(self, claim: str, evidence_list: List[Dict]) -> List[Dict]:
        """エビデンスリストの立場を分析"""
        analyzed_evidence = []
        
        for evidence in evidence_list:
            title = evidence.get("title", "")
            abstract = evidence.get("abstract", "")
            
            # タイトルとアブストラクトを結合
            evidence_text = f"{title}. {abstract}".strip()
            
            if len(evidence_text) < 10:
                # エビデンステキストが短すぎる場合
                stance_result = NLIResult("neutral", 0.3, "エビデンス情報が不足")
            else:
                # NLI分析
                stance_result = self.nli.analyze_claim_evidence_pair(claim, evidence_text)
            
            # エビデンス情報に立場分析結果を追加
            evidence_with_stance = evidence.copy()
            evidence_with_stance.update({
                "stance": stance_result.stance,
                "stance_confidence": stance_result.confidence,
                "stance_reasoning": stance_result.reasoning
            })
            
            analyzed_evidence.append(evidence_with_stance)
        
        return analyzed_evidence
    
    def get_stance_summary(self, analyzed_evidence: List[Dict]) -> Dict:
        """立場分析の要約"""
        if not analyzed_evidence:
            return {
                "support_count": 0,
                "contradict_count": 0,
                "neutral_count": 0,
                "overall_stance": "neutral",
                "confidence": 0.0
            }
        
        support_count = sum(1 for e in analyzed_evidence if e.get("stance") == "support")
        contradict_count = sum(1 for e in analyzed_evidence if e.get("stance") == "contradict")
        neutral_count = sum(1 for e in analyzed_evidence if e.get("stance") == "neutral")
        
        total = len(analyzed_evidence)
        
        # 全体的な立場の決定
        if support_count > contradict_count and support_count > neutral_count:
            overall_stance = "support"
            confidence = support_count / total
        elif contradict_count > support_count and contradict_count > neutral_count:
            overall_stance = "contradict"
            confidence = contradict_count / total
        else:
            overall_stance = "neutral"
            confidence = neutral_count / total if neutral_count > 0 else 0.5
        
        return {
            "support_count": support_count,
            "contradict_count": contradict_count,
            "neutral_count": neutral_count,
            "overall_stance": overall_stance,
            "confidence": confidence,
            "total_evidence": total
        }


def analyze_claim_evidence_stance(claim: str, evidence_list: List[Dict]) -> Tuple[List[Dict], Dict]:
    """メイン関数：主張とエビデンスの立場分析"""
    analyzer = EvidenceStanceAnalyzer()
    
    # 各エビデンスの立場を分析
    analyzed_evidence = analyzer.analyze_evidence_list(claim, evidence_list)
    
    # 全体的な立場の要約
    stance_summary = analyzer.get_stance_summary(analyzed_evidence)
    
    return analyzed_evidence, stance_summary