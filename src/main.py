from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from src.config import settings
from src.database import create_tables, get_db
from src.api.health import router as health_router
from src.api.score import router as score_router

# アプリケーション初期化
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="医学・健康情報のエビデンスを9軸100点ルーブリックで自動評価するAPI"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベース初期化
@app.on_event("startup")
async def startup_event():
    create_tables()

# ルーター登録
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(score_router, prefix=settings.api_v1_prefix, tags=["score"])

# ルートエンドポイント
@app.get("/")
async def root():
    return {
        "message": "Evidence Checker API",
        "version": settings.app_version,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)