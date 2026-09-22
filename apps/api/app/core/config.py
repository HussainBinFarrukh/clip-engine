from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://clip_engine:clip_engine@postgres:5432/clip_engine"
    redis_url: str = "redis://redis:6379/0"
    storage_root: str = "storage"
    max_upload_bytes: int = 500 * 1024 * 1024
    llm_provider: str = "gemini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
