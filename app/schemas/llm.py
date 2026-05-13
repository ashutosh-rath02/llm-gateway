from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ContextItem(BaseModel):
    type: str
    content: str


class ValidationErrorItem(BaseModel):
    path: str
    message: str


class ValidationSummary(BaseModel):
    schema_valid: bool
    business_rules_valid: bool | None = None
    errors: list[ValidationErrorItem] | None = None


class UsageSummary(BaseModel):
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    cost_usd: float


class FallbackSummary(BaseModel):
    used: bool
    level: int


class GatewayExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    feature: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    input: str = Field(min_length=1)
    context: list[ContextItem] = Field(default_factory=list)
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
    provider: Literal["mock", "openai_compatible"] | None = None
    routing_policy: Literal[
        "cost_optimized",
        "balanced",
        "quality_optimized",
        "explicit_model",
    ] = "balanced"
    risk_level: Literal["low", "medium", "high"] = "low"
    latency_budget_ms: int = Field(default=8000, gt=0)
    cost_budget_usd: float = Field(default=0.05, ge=0.0)
    requested_model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GatewayExecuteResponse(BaseModel):
    status: Literal["success", "validation_failed"]
    trace_id: str
    model: str
    output: Any | None
    validation: ValidationSummary | None = None
    usage: UsageSummary | None = None
    fallback: FallbackSummary
