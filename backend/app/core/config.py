from typing import List, Set, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Core Application Settings
    PROJECT_NAME: str = "NIDAN AI"
    PROJECT_TAGLINE: str = "Intelligent Clinical Insights"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # CDSS Disclaimer
    CDSS_DISCLAIMER: str = (
        "NIDAN AI provides assistive clinical insights for licensed medical professionals. "
        "It is not an automated diagnostic system and must never independently provide a "
        "definitive diagnosis, prescription, or treatment decision."
    )

    # Security & JWT
    SECRET_KEY: str = "insecure_default_secret_key_change_in_production_min_32_chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./nidan_ai_dev.db"

    # Redis / Task Queue
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage Abstraction
    STORAGE_BACKEND: str = "local"  # 'local', 's3', 'minio'
    STORAGE_LOCAL_ROOT: str = "./storage_data"
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    # File Ingestion & Security Settings (Phase 1)
    MAX_UPLOAD_SIZE_MB: int = 25  # Max 25 MB per document
    ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
    ALLOWED_MIME_TYPES: Set[str] = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
    }

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v


    # Doctor Copilot & LLM Settings (Phase 6)
    LLM_PROVIDER: str = "mock"  # 'mock', 'openai', 'anthropic', 'gemini'
    LLM_MODEL_NAME: str = "nidan-clinical-deterministic-v1"
    LLM_API_KEY: str = ""
    COPILOT_MAX_DOCUMENTS: int = 20
    COPILOT_MAX_OBSERVATIONS: int = 100
    COPILOT_MAX_FINDINGS: int = 50
    COPILOT_MAX_MEDICATIONS: int = 50
    COPILOT_MAX_NOTES: int = 20
    COPILOT_TIMEOUT_SECONDS: int = 30


settings = Settings()
