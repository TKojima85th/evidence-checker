from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./evidence_checker.db"
    
    # API
    app_name: str = "Evidence Checker API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    
    # External APIs
    ncbi_email: Optional[str] = None
    ncbi_api_key: Optional[str] = None
    
    # Processing
    max_claim_length: int = 5000
    processing_timeout: int = 3
    max_concurrent_requests: int = 10
    
    # Cache
    enable_cache: bool = False
    redis_url: Optional[str] = None
    cache_ttl: int = 3600
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()