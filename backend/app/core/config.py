import os
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict
# pyrefly: ignore [missing-import]
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Toruqx Secure RAG Engine"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database connections
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres_secure_password@localhost:5432/rag_db")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_API_KEY: str = Field(default="")

    # ML & API keys
    GEMINI_API_KEY: str = Field(default="")
    EMBEDDING_MODEL_NAME: str = Field(default="all-MiniLM-L6-v2")

    # Security settings — JWT_SECRET_KEY is REQUIRED, no insecure default
    JWT_SECRET_KEY: str = Field(...)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # CORS — restrict to known frontend origins in production
    CORS_ORIGINS: str = Field(default="http://localhost:3000")

    # Upload size limits
    MAX_UPLOAD_SIZE_MB: int = Field(default=50)

    # Turnstile settings
    TURNSTILE_SECRET_KEY: str = Field(default="")
    BYPASS_TURNSTILE: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
