from pathlib import Path
from typing import Any, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class ConfigurationError(ValueError):
    """Raised when application configuration is invalid for the specified environment."""
    pass


class Settings(BaseSettings):
    PROJECT_NAME: str = "Barabanki Connect"
    PROJECT_TAGLINE: str = "Empowering Citizens, Students, Businesses & Heritage in Barabanki"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security & CORS
    SECRET_KEY: str = "barabanki_connect_super_secret_local_dev_key_2026_xyz!"
    CSRF_SECRET: str = "barabanki_csrf_protection_key_2026_secure!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    SESSION_COOKIE_NAME: str = "barabanki_session"
    COOKIE_SECURE: bool = False  # Set to True in production HTTPS environments
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
    ]

    # Rate Limiting & Performance
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH_PER_MINUTE: int = 20
    RATE_LIMIT_SUBMIT_PER_MINUTE: int = 40
    STATIC_CACHE_MAX_AGE: int = 86400  # 24 hours in seconds

    # Database
    DATABASE_URL: str = "sqlite:///./barabanki.db"

    # Persistent Storage Configuration (url / s3 / cloudinary)
    STORAGE_BACKEND: str = "url"
    STORAGE_BUCKET: str = ""
    STORAGE_ENDPOINT_URL: str = ""
    STORAGE_ACCESS_KEY_ID: str = ""
    STORAGE_SECRET_ACCESS_KEY: str = ""
    STORAGE_PUBLIC_BASE_URL: str = ""

    # Seed Admin Credentials
    ADMIN_EMAIL: str = "admin@barabanki.local"
    ADMIN_PASSWORD: str = "Admin@123456"

    # Pagination & UI
    DEFAULT_PAGE_SIZE: int = 12

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip()
            # Standardize postgres:// prefix provided by Neon / Render to postgresql+psycopg2://
            if v_clean.startswith("postgres://"):
                v_clean = v_clean.replace("postgres://", "postgresql+psycopg2://", 1)
            elif v_clean.startswith("postgresql://") and not v_clean.startswith("postgresql+"):
                v_clean = v_clean.replace("postgresql://", "postgresql+psycopg2://", 1)
            return v_clean
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip()
            if v_clean.startswith("[") and v_clean.endswith("]"):
                import json
                try:
                    return json.loads(v_clean)
                except Exception:
                    pass
            return [origin.strip() for origin in v_clean.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_database(self) -> "Settings":
        if self.is_production:
            db = (self.DATABASE_URL or "").strip().lower()
            if not db or db.startswith("sqlite"):
                raise ConfigurationError(
                    "PRODUCTION MISCONFIGURATION: SQLite cannot be used in production mode on Render / cloud environments. "
                    "Render web services operate on ephemeral disks where SQLite data is lost across restarts and multi-worker locks fail. "
                    "Please configure a valid PostgreSQL connection string (such as Neon PostgreSQL) via the DATABASE_URL environment variable.\n"
                    "Example: postgresql+psycopg2://user:password@ep-cool-base-123456.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def effective_cookie_secure(self) -> bool:
        return self.COOKIE_SECURE or self.is_production

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
