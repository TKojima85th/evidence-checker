from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database import get_db
from src.config import settings

router = APIRouter()


@router.get("/")
async def health_check(db: Session = Depends(get_db)):
    try:
        # データベース接続確認
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "version": settings.app_version,
        "database": db_status,
        "timestamp": "2025-08-15T00:00:00Z"
    }