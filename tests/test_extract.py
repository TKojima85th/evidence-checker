import pytest
from src.core.extract import ClaimExtractor, extract_main_claim


class TestClaimExtractor:
    """主張抽出機能のテスト"""
    
    def setup_method(self):
        self.extractor = ClaimExtractor()
    
    def test_extract_causal_claim(self):
        """因果関係の主張抽出テスト"""
        text = "ビタミンDが免疫機能を向上させる"
        claims = self.extractor.extract_claims(text)
        
        assert len(claims) > 0
        assert claims[0].claim_type == "causal"
        assert claims[0].subject is not None
    
    def test_extract_effect_claim(self):
        """効果の主張抽出テスト"""
        text = "この治療により症状が50%改善した"
        claims = self.extractor.extract_claims(text)
        
        assert len(claims) > 0
        assert claims[0].claim_type == "effect"
        assert claims[0].effect_size is not None
    
    def test_extract_safety_claim(self):
        """安全性の主張抽出テスト"""
        text = "この薬は安全である"
        claims = self.extractor.extract_claims(text)
        
        assert len(claims) > 0
        assert claims[0].claim_type == "safety"
    
    def test_no_medical_keywords(self):
        """医学キーワードがない場合のテスト"""
        text = "今日は良い天気ですね"
        claims = self.extractor.extract_claims(text)
        
        assert len(claims) == 0
    
    def test_get_main_claim(self):
        """メイン主張抽出のテスト"""
        text = "ビタミンDは健康に良い。また、免疫機能を向上させる効果がある。"
        claim = self.extractor.get_main_claim(text)
        
        assert claim is not None
        assert claim.confidence > 0


class TestExtractMainClaim:
    """extract_main_claim関数のテスト"""
    
    def test_extract_main_claim_function(self):
        """メイン関数のテスト"""
        text = "ビタミンDが免疫システムをサポートする"
        result = extract_main_claim(text)
        
        assert "text" in result
        assert "confidence" in result
        assert "type" in result
        assert result["confidence"] > 0
    
    def test_extract_main_claim_no_claims(self):
        """主張が見つからない場合のテスト"""
        text = "こんにちは"
        result = extract_main_claim(text)
        
        assert result["confidence"] == 0.1
        assert result["type"] == "general"