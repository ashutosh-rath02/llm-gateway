from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.core.errors import GatewayError


@dataclass(slots=True)
class ProviderRequest:
    feature: str
    task_type: str
    input_text: str
    context: list[dict[str, Any]]
    schema: dict[str, Any] | None
    requested_model: str | None


@dataclass(slots=True)
class ProviderResponse:
    provider: str
    model: str
    output: Any
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    refusal: str | None = None


class ProviderError(GatewayError):
    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        status_code: int = 502,
    ) -> None:
        super().__init__(message, error_type=error_type, status_code=status_code)


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError
