"""
医学用語正規化モジュール (マルチAPI対応版)

一般的な健康・医学に関する表現を専門的な医学用語に変換し、
PubMed検索に適した中立的なクエリを生成する。
OpenAI, Gemini, DeepSeek APIに対応。
"""

import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from openai import OpenAI

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class NormalizedClaim:
    """正規化された主張データ"""
    original_text: str
    medical_terms: List[str]
    search_query: str
    key_concepts: List[str]
    medical_field: str
    intervention: Optional[str] = None
    outcome: Optional[str] = None
    population: Optional[str] = None
    confidence: float = 0.0
    api_used: str = "fallback"


class MedicalTermNormalizer:
    """医学用語正規化クラス（マルチAPI対応）"""
    
    def __init__(self, preferred_api: Optional[str] = None):
        """
        初期化
        
        Args:
            preferred_api: 使用するAPI ("openai", "gemini", "deepseek", "fallback")
        """
        self.preferred_api = preferred_api or settings.normalization_api
        self.clients = {}
        
        # OpenAI
        if settings.openai_api_key:
            try:
                self.clients["openai"] = OpenAI(api_key=settings.openai_api_key)
                logger.info("✅ OpenAI API クライアント初期化完了")
            except Exception as e:
                logger.warning(f"❌ OpenAI API 初期化失敗: {e}")
        
        # Gemini
        if settings.gemini_api_key and genai:
            try:
                genai.configure(api_key=settings.gemini_api_key)
                self.clients["gemini"] = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("✅ Gemini API クライアント初期化完了")
            except Exception as e:
                logger.warning(f"❌ Gemini API 初期化失敗: {e}")
        
        # DeepSeek (OpenAI互換)
        if settings.deepseek_api_key:
            try:
                self.clients["deepseek"] = OpenAI(
                    api_key=settings.deepseek_api_key,
                    base_url="https://api.deepseek.com"
                )
                logger.info("✅ DeepSeek API クライアント初期化完了")
            except Exception as e:
                logger.warning(f"❌ DeepSeek API 初期化失敗: {e}")
        
        logger.info(f"🔧 利用可能なAPI: {list(self.clients.keys())}")
        logger.info(f"🎯 優先API: {self.preferred_api}")
    
    def normalize_claim(self, claim_text: str, language: str = "ja", force_api: Optional[str] = None) -> NormalizedClaim:
        """
        主張を医学用語に正規化する
        
        Args:
            claim_text: 元の主張文
            language: 言語コード（ja/en）
            force_api: 強制的に使用するAPI（None=設定に従う）
            
        Returns:
            NormalizedClaim: 正規化結果
        """
        api_to_use = force_api or self.preferred_api
        
        # 利用可能なAPIの順序で試行
        apis_to_try = [api_to_use] if api_to_use in self.clients else []
        apis_to_try.extend([api for api in self.clients.keys() if api != api_to_use])
        
        if not apis_to_try:
            logger.warning("⚠️ 利用可能なAPIがありません。フォールバック正規化を実行します。")
            return self._fallback_normalize(claim_text)
        
        for api_name in apis_to_try:
            try:
                logger.info(f"🔄 {api_name} APIで正規化を試行中...")
                
                if api_name == "gemini":
                    result = self._normalize_with_gemini(claim_text, language)
                elif api_name in ["openai", "deepseek"]:
                    result = self._normalize_with_openai_compatible(claim_text, language, api_name)
                else:
                    continue
                
                result.api_used = api_name
                logger.info(f"✅ {api_name} APIで正規化成功 (信頼度: {result.confidence:.2f})")
                return result
                    
            except Exception as e:
                logger.warning(f"❌ {api_name} API正規化失敗: {str(e)}")
                continue
        
        logger.error("🚨 全てのAPI試行が失敗。フォールバック正規化を実行します。")
        return self._fallback_normalize(claim_text)
    
    def _normalize_with_openai_compatible(self, claim_text: str, language: str, api_name: str) -> NormalizedClaim:
        """OpenAI互換API（OpenAI/DeepSeek）での正規化"""
        client = self.clients[api_name]
        prompt = self._get_normalization_prompt(claim_text, language)
        
        model_name = "gpt-4o-mini" if api_name == "openai" else "deepseek-chat"
        system_msg = ("あなたは医学研究の専門家です。健康に関する一般的な表現を科学的で中立的な医学用語に正規化することが得意です。" 
                     if language == "ja" else 
                     "You are a medical research expert specializing in normalizing health claims into scientific terminology.")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        result = self._parse_json_response(content)
        
        confidence_boost = 0.9 if api_name == "openai" else 0.85
        
        return NormalizedClaim(
            original_text=claim_text,
            medical_terms=result.get("medical_terms", []),
            search_query=result.get("search_query", ""),
            key_concepts=result.get("key_concepts", []),
            medical_field=result.get("medical_field", "general"),
            intervention=result.get("intervention"),
            outcome=result.get("outcome"),
            population=result.get("population"),
            confidence=min(result.get("confidence", confidence_boost), 0.95),
            api_used=api_name
        )
    
    def _normalize_with_gemini(self, claim_text: str, language: str) -> NormalizedClaim:
        """Gemini APIでの正規化"""
        model = self.clients["gemini"]
        prompt = self._get_normalization_prompt(claim_text, language)
        
        response = model.generate_content(prompt)
        content = response.text.strip()
        result = self._parse_json_response(content)
        
        return NormalizedClaim(
            original_text=claim_text,
            medical_terms=result.get("medical_terms", []),
            search_query=result.get("search_query", ""),
            key_concepts=result.get("key_concepts", []),
            medical_field=result.get("medical_field", "general"),
            intervention=result.get("intervention"),
            outcome=result.get("outcome"),
            population=result.get("population"),
            confidence=min(result.get("confidence", 0.92), 0.95),  # Geminiは高品質
            api_used="gemini"
        )
    
    def _parse_json_response(self, content: str) -> dict:
        """APIレスポンスからJSONを抽出・パース"""
        # JSON部分を抽出
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "{" in content and "}" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            json_str = content[start:end]
        else:
            json_str = content
        
        return json.loads(json_str)
    
    def _get_normalization_prompt(self, claim_text: str, language: str) -> str:
        """正規化用プロンプトを生成"""
        if language == "ja":
            return f"""
以下の日本語の健康・医学に関する主張を分析し、医学研究に適した形式に正規化してください。

主張: "{claim_text}"

以下の情報をJSON形式で出力してください：

{{
    "medical_terms": ["専門的な医学用語のリスト"],
    "search_query": "PubMed検索用の英語クエリ（中立的な表現）",
    "key_concepts": ["評価対象となる核心概念"],
    "medical_field": "関連医学分野（例：cardiology, immunology, nutrition）",
    "intervention": "介入・要因（例：vitamin D, exercise, drug name）",
    "outcome": "結果・効果（例：immune function, mortality, disease risk）",
    "population": "対象集団（例：adults, elderly, patients）",
    "confidence": 0.0から1.0の数値（正規化の信頼度）
}}

重要な指針：
1. 検索クエリは中立的な表現を使用（"効果がある"→"effect", "良い"→"association"）
2. 医学用語は正確で具体的なものを選択
3. PubMed検索に適したキーワードを含める
4. バイアスのない客観的な表現に変換
"""
        else:
            return f"""
Analyze the following health/medical claim and normalize it for medical research.

Claim: "{claim_text}"

Output the following information in JSON format:

{{
    "medical_terms": ["list of specific medical terms"],
    "search_query": "neutral PubMed search query",
    "key_concepts": ["core concepts for evaluation"],
    "medical_field": "relevant medical field",
    "intervention": "intervention or factor",
    "outcome": "outcome or effect",
    "population": "target population",
    "confidence": "confidence score from 0.0 to 1.0"
}}

Guidelines:
1. Use neutral terminology for search queries
2. Convert subjective terms to objective medical language
3. Include relevant MeSH terms where appropriate
4. Focus on evidence-based terminology
"""
    
    def _fallback_normalize(self, claim_text: str) -> NormalizedClaim:
        """APIが利用できない場合のフォールバック正規化"""
        
        # 基本的なキーワード抽出
        medical_keywords = {
            "ビタミンD": ["vitamin D", "cholecalciferol"],
            "免疫": ["immune", "immunity", "immunomodulation"],
            "心臓": ["cardiac", "cardiovascular", "heart"],
            "血圧": ["blood pressure", "hypertension"],
            "コレステロール": ["cholesterol", "lipid"],
            "糖尿病": ["diabetes", "glucose", "insulin"],
            "運動": ["exercise", "physical activity"],
            "食事": ["diet", "nutrition", "dietary"],
            "オメガ3": ["omega-3", "n-3 fatty acids"],
            "緑茶": ["green tea", "catechins", "EGCG"],
        }
        
        search_terms = []
        key_concepts = []
        
        for japanese_term, english_terms in medical_keywords.items():
            if japanese_term in claim_text:
                search_terms.extend(english_terms)
                key_concepts.append(japanese_term)
        
        search_query = " ".join(search_terms) if search_terms else claim_text
        
        return NormalizedClaim(
            original_text=claim_text,
            medical_terms=search_terms,
            search_query=search_query,
            key_concepts=key_concepts,
            medical_field="general",
            confidence=0.3,  # フォールバックなので低い信頼度
            api_used="fallback"
        )
    
    def get_available_apis(self) -> List[str]:
        """利用可能なAPIのリストを取得"""
        return list(self.clients.keys()) + ["fallback"]
    
    def test_api_connection(self, api_name: str) -> bool:
        """指定されたAPIの接続テスト"""
        if api_name == "fallback":
            return True
            
        if api_name not in self.clients:
            return False
        
        try:
            test_claim = "test"
            if api_name == "gemini":
                model = self.clients[api_name]
                response = model.generate_content("Say 'OK' if you can understand this.")
                return "OK" in response.text
            else:
                client = self.clients[api_name]
                model_name = "gpt-4o-mini" if api_name == "openai" else "deepseek-chat"
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "Say 'OK'"}],
                    max_tokens=10
                )
                return "OK" in response.choices[0].message.content
        except Exception as e:
            logger.warning(f"API接続テスト失敗 ({api_name}): {e}")
            return False


# グローバルインスタンス
normalizer = MedicalTermNormalizer()