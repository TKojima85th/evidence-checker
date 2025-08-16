import pytest
from src.core.nli import MultilingualNLI, EvidenceStanceAnalyzer, analyze_claim_evidence_stance


class TestMultilingualNLI:
    """多言語NLIクラスのテスト"""
    
    def setup_method(self):
        self.nli = MultilingualNLI()
    
    def test_analyze_claim_evidence_support(self):
        """支持関係の検出テスト"""
        claim = "ビタミンDが免疫機能を向上させる"
        evidence = "研究によると、ビタミンDは免疫システムの機能を改善することが示されています"
        
        result = self.nli.analyze_claim_evidence_pair(claim, evidence)
        
        assert result.stance in ["support", "neutral"]
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.reasoning) > 0
    
    def test_analyze_claim_evidence_contradict(self):
        """矛盾関係の検出テスト"""
        claim = "ビタミンDは効果がある"
        evidence = "この研究では、ビタミンDに効果がないことが示されました"
        
        result = self.nli.analyze_claim_evidence_pair(claim, evidence)
        
        # 矛盾が検出されるか、少なくとも支持ではない
        assert result.stance in ["contradict", "neutral"]
        assert 0.0 <= result.confidence <= 1.0
    
    def test_analyze_claim_evidence_neutral(self):
        """中立関係の検出テスト"""
        claim = "ビタミンDが免疫機能を向上させる"
        evidence = "今日は良い天気です"
        
        result = self.nli.analyze_claim_evidence_pair(claim, evidence)
        
        assert result.stance == "neutral"
        assert 0.0 <= result.confidence <= 1.0
    
    def test_contradiction_patterns(self):
        """矛盾パターン検出のテスト"""
        claim = "治療は効果がある"
        evidence = "この治療には効果がない"
        
        contradiction_score = self.nli._detect_contradiction_patterns(claim, evidence)
        assert contradiction_score > 0.5
    
    def test_support_patterns(self):
        """支持パターン検出のテスト"""
        claim = "治療は効果がある"
        evidence = "この治療には大きな効果がある"
        
        support_score = self.nli._detect_support_patterns(claim, evidence)
        assert support_score > 0.5


class TestEvidenceStanceAnalyzer:
    """エビデンス立場分析クラスのテスト"""
    
    def setup_method(self):
        self.analyzer = EvidenceStanceAnalyzer()
    
    def test_analyze_evidence_list(self):
        """エビデンスリスト分析のテスト"""
        claim = "ビタミンDが免疫機能を向上させる"
        evidence_list = [
            {
                "title": "ビタミンDと免疫の関係",
                "abstract": "ビタミンDは免疫システムを強化する効果があります"
            },
            {
                "title": "ビタミンD研究",
                "abstract": "ビタミンDの効果は限定的である"
            }
        ]
        
        analyzed = self.analyzer.analyze_evidence_list(claim, evidence_list)
        
        assert len(analyzed) == 2
        for evidence in analyzed:
            assert "stance" in evidence
            assert "stance_confidence" in evidence
            assert "stance_reasoning" in evidence
            assert evidence["stance"] in ["support", "contradict", "neutral"]
    
    def test_get_stance_summary(self):
        """立場要約のテスト"""
        analyzed_evidence = [
            {"stance": "support", "stance_confidence": 0.8},
            {"stance": "support", "stance_confidence": 0.7},
            {"stance": "contradict", "stance_confidence": 0.6}
        ]
        
        summary = self.analyzer.get_stance_summary(analyzed_evidence)
        
        assert summary["support_count"] == 2
        assert summary["contradict_count"] == 1
        assert summary["neutral_count"] == 0
        assert summary["total_evidence"] == 3
        assert summary["overall_stance"] == "support"
        assert 0.0 <= summary["confidence"] <= 1.0
    
    def test_empty_evidence_list(self):
        """空のエビデンスリストのテスト"""
        summary = self.analyzer.get_stance_summary([])
        
        assert summary["support_count"] == 0
        assert summary["contradict_count"] == 0
        assert summary["neutral_count"] == 0
        assert summary["overall_stance"] == "neutral"
        assert summary["confidence"] == 0.0


class TestAnalyzeClaimEvidenceStance:
    """メイン関数のテスト"""
    
    def test_analyze_claim_evidence_stance_function(self):
        """メイン関数の統合テスト"""
        claim = "ビタミンDが免疫機能を向上させる"
        evidence_list = [
            {
                "title": "ビタミンD研究",
                "abstract": "ビタミンDは免疫機能を改善することが確認されました"
            }
        ]
        
        analyzed_evidence, stance_summary = analyze_claim_evidence_stance(claim, evidence_list)
        
        assert len(analyzed_evidence) == 1
        assert "stance" in analyzed_evidence[0]
        assert "stance_confidence" in analyzed_evidence[0]
        
        assert "support_count" in stance_summary
        assert "contradict_count" in stance_summary
        assert "neutral_count" in stance_summary
        assert "overall_stance" in stance_summary
        assert "confidence" in stance_summary
    
    def test_no_evidence(self):
        """エビデンスなしの場合のテスト"""
        claim = "ビタミンDが免疫機能を向上させる"
        evidence_list = []
        
        analyzed_evidence, stance_summary = analyze_claim_evidence_stance(claim, evidence_list)
        
        assert len(analyzed_evidence) == 0
        assert stance_summary["total_evidence"] == 0
        assert stance_summary["overall_stance"] == "neutral"