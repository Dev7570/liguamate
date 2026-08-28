"""LinguaMate AI - Configuration"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./linguamate.db"
    sync_database_url: str = "sqlite:///./linguamate.db"

    # Redis (Optional)
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "linguamate-secret-key-super-secure-change-in-prod-12345"
    access_token_expire_minutes: int = 1440
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # AI Provider Settings (Supports OpenAI, Groq, or Gemini)
    openai_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    openai_model: str = "llama3-70b-8192"  # Default model for Groq

    # App
    app_name: str = "LinguaMate AI"
    debug: bool = True
    frontend_url: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
