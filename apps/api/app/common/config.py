from functools import lru_cache
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Settings
    APP_ENV: str = "development"
    APP_NAME: str = "smart-study-planner"
    DEBUG: bool = True
    VERSION: str = "0.1.0"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production-min-32-chars-long"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smart_study_planner"
    TEST_DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smart_study_planner_test"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Cache & Queues (Valkey / Redis)
    VALKEY_URL: str = "redis://localhost:6379/0"

    # Object Storage (SeaweedFS / S3 compatible)
    OBJECT_STORAGE_ENDPOINT: str = "http://localhost:8333"
    OBJECT_STORAGE_BUCKET: str = "study-planner"
    OBJECT_STORAGE_ACCESS_KEY: str = "dev_access_key"
    OBJECT_STORAGE_SECRET_KEY: str = "dev_secret_key"

    # AI / LLM Configuration
    LLM_PROVIDER: str = "ollama"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen3:8b"
    OLLAMA_LITE_MODEL: str = "qwen2.5-coder:1.5b"

    # Embeddings & Rerankers
    EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-0.6B"
    RERANKER_MODEL: str = "Qwen/Qwen3-Reranker-0.6B"

    # Web Research
    SEARCH_PROVIDER: str = "searxng"
    SEARXNG_URL: str = "http://localhost:8080"

    # Versions
    FSRS_VERSION: str = "fsrs-v4"
    BKT_VERSION: str = "bkt-v1"
    PRIORITY_VERSION: str = "priority-v1"
    PLANNER_VERSION: str = "planner-v1"

    # MongoDB Configuration (Product & User Store)
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "smart_study_planner"

    # Google AI Configuration
    GOOGLE_API_KEY: Union[str, None] = None
    GOOGLE_AI_MODEL: str = "gemini-2.5-flash"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
