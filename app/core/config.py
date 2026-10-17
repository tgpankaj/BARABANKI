import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "Barabanki Connect"
    PROJECT_TAGLINE: str = "Empowering Citizens, Students, Businesses & Heritage in Barabanki"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = "barabanki_connect_super_secret_local_dev_key_2026_xyz!"
    CSRF_SECRET: str = "barabanki_csrf_protection_key_2026_secure!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    SESSION_COOKIE_NAME: str = "barabanki_session"

    # Database
    DATABASE_URL: str = "sqlite:///./barabanki.db"

    # Seed Admin Credentials
    ADMIN_EMAIL: str = "admin@barabanki.local"
    ADMIN_PASSWORD: str = "Admin@123456"

    # Pagination & UI
    DEFAULT_PAGE_SIZE: int = 12

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
