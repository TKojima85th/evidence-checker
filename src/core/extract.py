import spacy
import re
from typing import List, Dict, Optional
from dataclasses import dataclass

# GiNZAモデルの初期化（グローバルで一度だけロード）
try:
    nlp = spacy.load("ja_ginza")
except OSError:
    # GiNZAモデルがない場合のフォールバック
    nlp = None


@dataclass
class ExtractedClaim:
    """抽出された主張の情報"""
    text: str
    confidence: float
    claim_type: str  # "causal", "effect", "safety", "general"
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None
    effect_size: Optional[str] = None


class ClaimExtractor:
    """日本語テキストから医学・健康関連の主張を抽出するクラス"""
    
    def __init__(self):
        self.nlp = nlp
        
        # 医学・健康関連の主張パターン（正規表現）
        self.causal_patterns = [
            r"(.+?)が(.+?)を(引き起こす|誘発する|原因となる|もたらす)",
            r"(.+?)により(.+?)が(改善|悪化|増加|減少|向上|低下)する",
            r"(.+?)は(.+?)に(効果的|有効|効く|良い|悪い)",
            r"(.+?)を摂取すると(.+?)が(上がる|下がる|改善|悪化)する"
        ]
        
        self.effect_patterns = [
            r"(.+?)は(.+?)に(\d+[%％]|倍|分の\d+)の(効果|影響|改善|悪化)",
            r"(.+?)により(.+?)が(\d+[%％]|倍)?(向上|改善|増加|減少|低下)",
            r"(\d+[%％]|倍)の(.+?)で(.+?)が(改善|悪化)"
        ]
        
        self.safety_patterns = [
            r"(.+?)は(安全|危険|有害|無害)である",
            r"(.+?)に(副作用|リスク|害|問題)は(ない|ある)",
            r"(.+?)を使用すると(.+?)のリスクが(増加|減少|高まる|下がる)"
        ]
        
        # 医学・健康関連キーワード
        self.medical_keywords = {
            "病気", "疾患", "症状", "治療", "薬", "サプリメント", "ビタミン", "ミネラル",
            "免疫", "感染", "ウイルス", "細菌", "がん", "癌", "心臓病", "糖尿病",
            "高血圧", "コレステロール", "血糖値", "血圧", "健康", "医療", "医学",
            "診断", "検査", "予防", "ワクチン", "接種", "食事", "運動", "睡眠"
        }
    
    def extract_claims(self, text: str) -> List[ExtractedClaim]:
        """テキストから主張を抽出"""
        if not self.nlp:
            # GiNZAが利用できない場合は正規表現のみで処理
            return self._extract_with_regex(text)
        
        claims = []
        
        # spaCyによる解析
        doc = self.nlp(text)
        
        # 文単位で処理
        for sent in doc.sents:
            sent_text = sent.text.strip()
            if len(sent_text) < 10:  # 短すぎる文はスキップ
                continue
                
            # 医学・健康関連キーワードが含まれているかチェック
            if not self._contains_medical_keywords(sent_text):
                continue
            
            # パターンマッチングで主張を抽出
            claim = self._extract_claim_from_sentence(sent_text)
            if claim:
                claims.append(claim)
        
        return claims
    
    def _extract_with_regex(self, text: str) -> List[ExtractedClaim]:
        """正規表現のみで主張を抽出（フォールバック）"""
        claims = []
        sentences = re.split(r'[。！？\n]', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
                
            if not self._contains_medical_keywords(sentence):
                continue
            
            claim = self._extract_claim_from_sentence(sentence)
            if claim:
                claims.append(claim)
        
        return claims
    
    def _contains_medical_keywords(self, text: str) -> bool:
        """医学・健康関連キーワードが含まれているかチェック"""
        return any(keyword in text for keyword in self.medical_keywords)
    
    def _extract_claim_from_sentence(self, sentence: str) -> Optional[ExtractedClaim]:
        """文から主張を抽出"""
        # 因果関係パターン
        for pattern in self.causal_patterns:
            match = re.search(pattern, sentence)
            if match:
                return ExtractedClaim(
                    text=sentence,
                    confidence=0.8,
                    claim_type="causal",
                    subject=match.group(1).strip(),
                    predicate=match.group(3).strip() if len(match.groups()) >= 3 else None,
                    object=match.group(2).strip()
                )
        
        # 効果パターン
        for pattern in self.effect_patterns:
            match = re.search(pattern, sentence)
            if match:
                effect_size = None
                groups = match.groups()
                for group in groups:
                    if re.search(r'\d+[%％]|倍', str(group)):
                        effect_size = group
                        break
                
                return ExtractedClaim(
                    text=sentence,
                    confidence=0.7,
                    claim_type="effect",
                    effect_size=effect_size
                )
        
        # 安全性パターン
        for pattern in self.safety_patterns:
            match = re.search(pattern, sentence)
            if match:
                return ExtractedClaim(
                    text=sentence,
                    confidence=0.6,
                    claim_type="safety",
                    subject=match.group(1).strip()
                )
        
        # 一般的な医学・健康主張（キーワードベース）
        if self._contains_medical_keywords(sentence):
            return ExtractedClaim(
                text=sentence,
                confidence=0.4,
                claim_type="general"
            )
        
        return None
    
    def get_main_claim(self, text: str) -> Optional[ExtractedClaim]:
        """テキストからメインの主張を1つ抽出"""
        claims = self.extract_claims(text)
        if not claims:
            return None
        
        # 信頼度が最も高い主張を返す
        return max(claims, key=lambda c: c.confidence)


def extract_main_claim(text: str) -> Dict:
    """メイン関数：テキストからメインの主張を抽出"""
    extractor = ClaimExtractor()
    claim = extractor.get_main_claim(text)
    
    if claim:
        return {
            "text": claim.text,
            "confidence": claim.confidence,
            "type": claim.claim_type,
            "subject": claim.subject,
            "predicate": claim.predicate,
            "object": claim.object,
            "effect_size": claim.effect_size
        }
    else:
        return {
            "text": text[:200] + "..." if len(text) > 200 else text,
            "confidence": 0.1,
            "type": "general",
            "subject": None,
            "predicate": None,
            "object": None,
            "effect_size": None
        }