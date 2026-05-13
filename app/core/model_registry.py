from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelProfile:
    name: str
    provider: str
    quality_rank: int
    latency_rank: int
    estimated_latency_ms: int
    max_context_tokens: int
    supports_structured_output: bool


MODEL_REGISTRY: dict[str, list[ModelProfile]] = {
    "mock": [
        ModelProfile(
            name="mock-fast-small",
            provider="mock",
            quality_rank=1,
            latency_rank=1,
            estimated_latency_ms=5,
            max_context_tokens=1_000_000,
            supports_structured_output=True,
        )
    ],
    "openai_compatible": [
        ModelProfile(
            name="gpt-5-nano",
            provider="openai_compatible",
            quality_rank=1,
            latency_rank=1,
            estimated_latency_ms=500,
            max_context_tokens=128_000,
            supports_structured_output=True,
        ),
        ModelProfile(
            name="gpt-5-mini",
            provider="openai_compatible",
            quality_rank=2,
            latency_rank=1,
            estimated_latency_ms=900,
            max_context_tokens=128_000,
            supports_structured_output=True,
        ),
        ModelProfile(
            name="gpt-5.4-mini",
            provider="openai_compatible",
            quality_rank=3,
            latency_rank=2,
            estimated_latency_ms=1_300,
            max_context_tokens=128_000,
            supports_structured_output=True,
        ),
        ModelProfile(
            name="gpt-5.4",
            provider="openai_compatible",
            quality_rank=4,
            latency_rank=3,
            estimated_latency_ms=2_500,
            max_context_tokens=128_000,
            supports_structured_output=True,
        ),
        ModelProfile(
            name="gpt-5.5",
            provider="openai_compatible",
            quality_rank=5,
            latency_rank=4,
            estimated_latency_ms=3_500,
            max_context_tokens=128_000,
            supports_structured_output=True,
        ),
    ],
}


def get_models_for_provider(provider_name: str) -> list[ModelProfile]:
    return MODEL_REGISTRY.get(provider_name, [])
