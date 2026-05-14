from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthKeySettings(BaseModel):
    name: str
    role: Literal["admin", "tenant"] = "tenant"
    tenant_id: str | None = None
    allowed_features: list[str] = Field(default_factory=list)


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
    execute_rate_limit_enabled: bool = True
    execute_rate_limit_requests: int = 60
    execute_rate_limit_window_seconds: int = 60
    max_request_latency_budget_ms: int = 30_000
    max_request_cost_budget_usd: float = 2.0
    store_prompts: bool = False
    store_outputs: bool = False
    hash_user_ids: bool = True
    trace_persistence_enabled: bool = True
    auth_enabled: bool = False
    auth_api_keys: dict[str, AuthKeySettings] = Field(default_factory=dict)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
