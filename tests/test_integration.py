import pytest
import time
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


class TestFullPipeline:
    """エンドツーエンドの統合テスト"""
    
    def test_complete_evaluation_pipeline(self):
        """完全な評価パイプラインのテスト"""
        test_claim = {
            "claim_text": "ビタミンDは免疫機能をサポートする効果があります",
            "topic": "health",
            "lang": "ja"
        }
        
        start_time = time.time()
        response = client.post("/api/v1/score", json=test_claim)
        end_time = time.time()
        
        # レスポンス確認
        assert response.status_code == 200
        data = response.json()
        
        # 基本フィールドの確認
        assert "total_score" in data
        assert "label" in data
        assert "axis_scores" in data
        assert "rationales" in data
        assert "evidence_top3" in data
        assert "metadata" in data
        
        # スコア範囲の確認
        assert 0 <= data["total_score"] <= 100
        
        # ラベルの確認
        valid_labels = ["True", "Mostly True", "Unsupported", "False", "Fabricated"]
        assert data["label"] in valid_labels
        
        # 9軸スコアの確認
        axis_scores = data["axis_scores"]
        for axis, score in axis_scores.items():
            assert 0 <= score <= 5
        
        # エビデンスの確認
        assert len(data["evidence_top3"]) > 0
        for evidence in data["evidence_top3"]:
            assert "source" in evidence
            assert "title" in evidence
            assert "stance" in evidence
            assert evidence["stance"] in ["support", "contradict", "neutral"]
        
        # 処理時間の確認
        processing_time = end_time - start_time
        assert processing_time < 30  # 30秒以内
    
    def test_health_medical_claim(self):
        """医学関連主張のテスト"""
        test_claim = {
            "claim_text": "定期的な運動は心臓病のリスクを減少させる",
            "topic": "health"
        }
        
        response = client.post("/api/v1/score", json=test_claim)
        assert response.status_code == 200
        
        data = response.json()
        # 医学関連の主張は通常ある程度のスコアを持つはず
        assert data["total_score"] > 20
    
    def test_harmful_claim_detection(self):
        """有害な主張の検出テスト"""
        test_claim = {
            "claim_text": "ワクチンは不要で危険です",
            "topic": "health"
        }
        
        response = client.post("/api/v1/score", json=test_claim)
        assert response.status_code == 200
        
        data = response.json()
        # 有害な主張は低いスコアを持つはず
        assert data["total_score"] <= 74  # "根拠薄い"まで制限
        assert data["label"] in ["Unsupported", "False", "Fabricated"]
    
    def test_multiple_concurrent_requests(self):
        """同時リクエストのテスト"""
        import concurrent.futures
        
        def make_request():
            test_claim = {
                "claim_text": "ビタミンCは風邪予防に効果的です",
                "topic": "health"
            }
            response = client.post("/api/v1/score", json=test_claim)
            return response.status_code == 200
        
        # 5つの同時リクエスト
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # すべてのリクエストが成功することを確認
        assert all(results)


class TestPerformance:
    """パフォーマンステスト"""
    
    def test_response_time_under_load(self):
        """負荷下でのレスポンス時間テスト"""
        test_claims = [
            "ビタミンDは骨の健康に重要です",
            "定期的な運動は健康に良い",
            "バランスの取れた食事が大切です",
            "十分な睡眠は免疫力を高める",
            "ストレス管理は心の健康に重要"
        ]
        
        response_times = []
        
        for claim_text in test_claims:
            test_claim = {
                "claim_text": claim_text,
                "topic": "health"
            }
            
            start_time = time.time()
            response = client.post("/api/v1/score", json=test_claim)
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        # 平均レスポンス時間が20秒以内
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 20
        
        # 最大レスポンス時間が30秒以内
        max_response_time = max(response_times)
        assert max_response_time < 30
    
    def test_memory_usage_stability(self):
        """メモリ使用量の安定性テスト"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 10回のリクエストを実行
        for i in range(10):
            test_claim = {
                "claim_text": f"健康に関する主張 {i}",
                "topic": "health"
            }
            
            response = client.post("/api/v1/score", json=test_claim)
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # メモリ増加が100MB以下であることを確認
        assert memory_increase < 100 * 1024 * 1024


class TestErrorHandling:
    """エラーハンドリングのテスト"""
    
    def test_invalid_input_handling(self):
        """無効な入力のハンドリングテスト"""
        # 空の主張
        response = client.post("/api/v1/score", json={"claim_text": ""})
        assert response.status_code == 400
        
        # 長すぎる主張
        long_text = "a" * 6000
        response = client.post("/api/v1/score", json={"claim_text": long_text})
        assert response.status_code == 400
        
        # 必須フィールドなし
        response = client.post("/api/v1/score", json={})
        assert response.status_code == 422  # Validation error
    
    def test_system_error_fallback(self):
        """システムエラー時のフォールバックテスト"""
        # 通常のリクエスト（エラーが発生してもフォールバックで処理される）
        test_claim = {
            "claim_text": "何らかの健康に関する主張",
            "topic": "health"
        }
        
        response = client.post("/api/v1/score", json=test_claim)
        # エラーが発生してもフォールバック処理で200が返される
        assert response.status_code == 200
        
        data = response.json()
        assert "total_score" in data
        assert "label" in data