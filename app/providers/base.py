from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


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
    model: str
    output: Any
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError

