from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Distributed Job Queue System"
    API_V1_PREFIX: str = "/api"
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/jobqueue",
        description="Async SQLAlchemy database URL. Supports PostgreSQL and SQLite (e.g. sqlite+aiosqlite:///./jobqueue.db)"
    )
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # Security
    SECRET_KEY: str = Field(
        default="super-secret-distributed-job-queue-key-change-in-prod-2026",
        description="Secret key for JWT generation"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ]
    
    # Default Admin Credentials
    ADMIN_EMAIL: str = "admin@jobqueue.io"
    ADMIN_PASSWORD: str = "Admin@123456"
    
    # Job Queue Configurations
    DEFAULT_MAX_RETRIES: int = 3
    RETRY_BACKOFF_BASE_SECONDS: int = 5
    DEFAULT_JOB_TIMEOUT_SECONDS: int = 120
    LEASE_TIMEOUT_SECONDS: int = 30
    WORKER_HEARTBEAT_INTERVAL_SECONDS: int = 5
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


settings = Settings()
