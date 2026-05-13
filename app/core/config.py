from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LLM Gateway"
    environment: str = "local"
    log_level: str = "INFO"
    api_prefix: str = "/v1"
    default_provider: str = "mock"
    default_model: str = "mock-fast-small"
    openai_default_model: str = "gpt-5.4-mini"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/llm_gateway"
    provider_timeout_ms: int = 15000
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    repair_retry_enabled: bool = True
    max_repair_attempts_per_model: int = 1
    repair_prompt_version: str = "repair_v1"
    store_prompts: bool = False
    store_outputs: bool = False
    hash_user_ids: bool = True
    trace_persistence_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
