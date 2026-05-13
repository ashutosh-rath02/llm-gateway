from app.core.config import get_settings
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider
from app.providers.openai_compatible import OpenAICompatibleProvider


class ProviderFactory:
    def get_provider(self, provider_name: str | None = None) -> LLMProvider:
        settings = get_settings()
        name = provider_name or settings.default_provider

        if name == "mock":
            return MockProvider(default_model=settings.default_model)
        if name == "openai_compatible":
            return OpenAICompatibleProvider(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                default_model=settings.openai_default_model,
                timeout_ms=settings.provider_timeout_ms,
            )

        raise ValueError(f"Unsupported provider '{name}'.")
