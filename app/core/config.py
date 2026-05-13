from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LLM Gateway"
    environment: str = "local"
    log_level: str = "INFO"
    api_prefix: str = "/v1"
    default_provider: str = "mock"
    default_model: str = "mock-fast-small"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/llm_gateway"
    redis_url: str = "redis://localhost:6379/0"
    provider_timeout_ms: int = 15000
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    store_prompts: bool = False
    store_outputs: bool = False
    hash_user_ids: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

