from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelPricing:
    input_per_token_usd: float
    cached_input_per_token_usd: float
    output_per_token_usd: float


MODEL_PRICING: dict[str, ModelPricing] = {
    "mock-fast-small": ModelPricing(
        input_per_token_usd=0.00015 / 1000,
        cached_input_per_token_usd=0.0,
        output_per_token_usd=0.0006 / 1000,
    ),
    "gpt-5.5": ModelPricing(
        input_per_token_usd=5.00 / 1_000_000,
        cached_input_per_token_usd=0.50 / 1_000_000,
        output_per_token_usd=30.00 / 1_000_000,
    ),
    "gpt-5.4": ModelPricing(
        input_per_token_usd=2.50 / 1_000_000,
        cached_input_per_token_usd=0.25 / 1_000_000,
        output_per_token_usd=15.00 / 1_000_000,
    ),
    "gpt-5.4-mini": ModelPricing(
        input_per_token_usd=0.75 / 1_000_000,
        cached_input_per_token_usd=0.075 / 1_000_000,
        output_per_token_usd=4.50 / 1_000_000,
    ),
    "gpt-5.4-nano": ModelPricing(
        input_per_token_usd=0.20 / 1_000_000,
        cached_input_per_token_usd=0.02 / 1_000_000,
        output_per_token_usd=1.25 / 1_000_000,
    ),
    "gpt-5-mini": ModelPricing(
        input_per_token_usd=0.25 / 1_000_000,
        cached_input_per_token_usd=0.025 / 1_000_000,
        output_per_token_usd=2.00 / 1_000_000,
    ),
    "gpt-5-nano": ModelPricing(
        input_per_token_usd=0.05 / 1_000_000,
        cached_input_per_token_usd=0.005 / 1_000_000,
        output_per_token_usd=0.40 / 1_000_000,
    ),
}


def resolve_pricing_model(model: str) -> str:
    if model in MODEL_PRICING:
        return model

    for candidate in sorted(MODEL_PRICING, key=len, reverse=True):
        if model.startswith(f"{candidate}-"):
            return candidate

    return "mock-fast-small"


def calculate_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    pricing = MODEL_PRICING[resolve_pricing_model(model)]
    non_cached_input_tokens = max(input_tokens - cached_input_tokens, 0)

    total = (
        non_cached_input_tokens * pricing.input_per_token_usd
        + cached_input_tokens * pricing.cached_input_per_token_usd
        + output_tokens * pricing.output_per_token_usd
    )
    return round(total, 6)
