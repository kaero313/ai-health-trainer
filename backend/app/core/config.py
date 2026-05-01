from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Health Trainer"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/health_trainer"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/health_trainer"
    REDIS_URL: str = "redis://localhost:6379/0"
    OPENSEARCH_URL: str = "http://localhost:9200"

    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    GEMINI_API_KEY: str = ""

    AI_DEFAULT_MODEL: str = "gemini-3-flash-preview"
    AI_ADVANCED_MODEL: str = "gemini-2.5-pro"
    AI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    AI_MAX_OUTPUT_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.7
    AI_DAILY_REQUEST_LIMIT: int = 30

    RAG_OPENSEARCH_INDEX: str = "rag_chunks_v1"
    RAG_OPENSEARCH_ALIAS: str = "rag_chunks_current"
    RAG_VECTOR_WEIGHT: float = 0.65
    RAG_KEYWORD_WEIGHT: float = 0.35

    UPLOAD_DIR: str = "/data/uploads"
    MAX_IMAGE_SIZE_MB: int = 10

    BACKEND_CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
        ]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        enable_decoding=False,
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
