from app.core.config import get_settings
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider
from app.providers.openai_compatible import OpenAICompatibleProvider


class ProviderFactory:
    def __init__(self) -> None:
        self.settings = get_settings()

    def get_provider(self, provider_name: str | None = None) -> LLMProvider:
        name = provider_name or self.settings.default_provider

        if name == "mock":
            return MockProvider(default_model=self.settings.default_model)
        if name == "openai_compatible":
            return OpenAICompatibleProvider(default_model=self.settings.default_model)

        raise ValueError(f"Unsupported provider '{name}'.")

