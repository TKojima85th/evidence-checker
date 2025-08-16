import pytest
from src.core.scoring import EvidenceScorer, calculate_evidence_score, ScoreComponents
from src.core.extract import ExtractedClaim


class TestEvidenceScorer:
    """エビデンススコアリングのテスト"""
    
    def setup_method(self):
        self.scorer = EvidenceScorer()
    
    def test_score_clarity_high(self):
        """高い明確性のテスト"""
        claim = ExtractedClaim(
            text="ビタミンD 1000IUを6ヶ月摂取することで免疫機能が20%向上する",
            confidence=0.8,
            claim_type="causal",
            subject="ビタミンD 1000IU",
            predicate="向上する",
            object="免疫機能",
            effect_size="20%"
        )
        
        score = self.scorer._score_clarity(claim)
        assert score >= 4
    
    def test_score_clarity_low(self):
        """低い明確性のテスト"""
        claim = ExtractedClaim(
            text="体に良い",
            confidence=0.3,
            claim_type="general"
        )
        
        score = self.scorer._score_clarity(claim)
        assert score <= 2
    
    def test_score_evidence_quality_high(self):
        """高品質エビデンスのテスト"""
        evidence_list = [
            {"study_type": "meta-analysis", "title": "メタ解析研究"},
            {"study_type": "randomized_controlled_trial", "title": "RCT研究"}
        ]
        
        score = self.scorer._score_evidence_quality(evidence_list)
        assert score >= 4
    
    def test_score_evidence_quality_low(self):
        """低品質エビデンスのテスト"""
        evidence_list = [
            {"study_type": "case_report", "title": "症例報告"}
        ]
        
        score = self.scorer._score_evidence_quality(evidence_list)
        assert score <= 2
    
    def test_score_harm_potential_dangerous(self):
        """危険な内容のテスト"""
        text = "ワクチンは不要です"
        score = self.scorer._score_harm_potential(text)
        assert score <= 1
    
    def test_score_harm_potential_safe(self):
        """安全な内容のテスト"""
        text = "バランスの良い食事が健康に重要です。医師に相談してください。"
        score = self.scorer._score_harm_potential(text)
        assert score >= 4
    
    def test_comprehensive_score_calculation(self):
        """包括的スコア計算のテスト"""
        claim = ExtractedClaim(
            text="ビタミンDが免疫機能をサポートする",
            confidence=0.7,
            claim_type="causal",
            subject="ビタミンD",
            object="免疫機能"
        )
        
        evidence_list = [
            {"study_type": "randomized_controlled_trial", "title": "RCT研究"}
        ]
        
        result = self.scorer.calculate_comprehensive_score(
            claim, evidence_list, "ビタミンDが免疫機能をサポートする"
        )
        
        assert "total_score" in result
        assert "label" in result
        assert "scores" in result
        assert 0 <= result["total_score"] <= 100


class TestCalculateEvidenceScore:
    """calculate_evidence_score関数のテスト"""
    
    def test_calculate_evidence_score_function(self):
        """メイン関数のテスト"""
        claim_dict = {
            "text": "ビタミンDが免疫機能をサポートする",
            "confidence": 0.7,
            "type": "causal",
            "subject": "ビタミンD",
            "object": "免疫機能"
        }
        
        evidence_list = [
            {"study_type": "randomized_controlled_trial", "title": "RCT研究"}
        ]
        
        result = calculate_evidence_score(
            claim_dict, evidence_list, "ビタミンDが免疫機能をサポートする"
        )
        
        assert "total_score" in result
        assert "label" in result
        assert result["total_score"] >= 0
        assert result["total_score"] <= 100
    
    def test_harmful_content_score_limit(self):
        """有害コンテンツのスコア制限テスト"""
        claim_dict = {
            "text": "ワクチンは不要",
            "confidence": 0.5,
            "type": "general"
        }
        
        evidence_list = []
        
        result = calculate_evidence_score(
            claim_dict, evidence_list, "ワクチンは不要です"
        )
        
        # 有害な内容は最大でも"根拠薄い"まで
        assert result["total_score"] <= 74