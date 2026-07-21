"""
Centralized configuration.

Every setting the app needs comes from here, not from scattered os.getenv()
calls. Values are loaded from environment variables / a .env file and
validated once at startup, so a missing key fails immediately and loudly
instead of causing a confusing error three requests later.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    GEMINI_API_KEY: str
    TAVILY_API_KEY: str
    OPENROUTER_API_KEY: str = ""  # optional


    # --- App ---
    app_name: str = "Silki AI"
    environment: str = "development"  # development | production
    debug: bool = True

    # --- Security ---
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    access_token_expire_minutes: int = 60 * 24  # 1 day
    refresh_token_expire_days: int = 30
    jwt_algorithm: str = "HS256"

    # --- CORS ---
    # Comma-separated list in .env, e.g. "https://silki.app,https://www.silki.app"
    # --- CORS ---
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5500,http://127.0.0.1:5500,"
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:8080,http://127.0.0.1:8080,"
        "http://localhost:8000,http://127.0.0.1:8000"
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # --- Database ---
    # SQLite by default (zero setup, free). Swap to a Postgres URL later
    # without changing any application code — SQLAlchemy abstracts it.
    database_url: str = "sqlite+aiosqlite:///./silki.db"

    # --- LLM providers (Groq — free tier) ---
    groq_api_key: str = ""
    groq_models: List[str] = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-8b-8192",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    # --- HuggingFace (free inference API) ---
    hf_token: str = ""
    hf_image_model: str = "black-forest-labs/FLUX.1-schnell"
    hf_asr_model: str = "openai/whisper-large-v3"

    # --- Rate limiting ---
    rate_limit_chat: str = "20/minute"
    rate_limit_image: str = "10/minute"
    rate_limit_auth: str = "10/minute"

    # --- Session limits ---
    max_history_messages: int = 40  # 20 exchanges kept per session


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so we parse the environment exactly once."""
    return Settings()
