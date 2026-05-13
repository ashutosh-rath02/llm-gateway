from app.providers.base import LLMProvider, ProviderRequest, ProviderResponse


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, default_model: str) -> None:
        self.default_model = default_model

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError(
            "OpenAI-compatible provider is scaffolded but not implemented yet."
        )

