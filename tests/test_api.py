import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_root_endpoint():
    """ルートエンドポイントのテスト"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Evidence Checker API"


def test_health_endpoint():
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_score_endpoint_valid_claim():
    """有効な主張でのスコアエンドポイントテスト"""
    test_claim = {
        "claim_text": "ビタミンDは免疫機能をサポートする",
        "topic": "health",
        "lang": "ja"
    }
    
    response = client.post("/api/v1/score", json=test_claim)
    assert response.status_code == 200
    
    data = response.json()
    assert "total_score" in data
    assert "label" in data
    assert "axis_scores" in data
    assert 0 <= data["total_score"] <= 100


def test_score_endpoint_empty_claim():
    """空の主張でのエラーテスト"""
    test_claim = {
        "claim_text": "",
        "topic": "health"
    }
    
    response = client.post("/api/v1/score", json=test_claim)
    assert response.status_code == 400


def test_score_endpoint_too_long_claim():
    """長すぎる主張でのエラーテスト"""
    test_claim = {
        "claim_text": "a" * 6000,  # 5000文字制限を超える
        "topic": "health"
    }
    
    response = client.post("/api/v1/score", json=test_claim)
    assert response.status_code == 400