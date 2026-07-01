from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables (or a .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ContextGate"
    env: str = "development"

    database_url: str = (
        "postgresql+asyncpg://contextgate:contextgate@postgres:5432/contextgate"
    )
    redis_url: str = "redis://redis:6379/0"

    cache_similarity_threshold: float = 0.88
    embedding_dimensions: int = 384

    default_provider: str = "mock"
    gemini_api_key: str = ""

    worker_timeout_seconds: int = 15

    # Redis stream + consumer group used by the async queue.
    request_stream: str = "llm_requests"
    consumer_group: str = "contextgate-workers"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
