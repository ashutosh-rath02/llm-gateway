from datetime import datetime

from pydantic import BaseModel

from app.schemas.llm import FallbackSummary, UsageSummary, ValidationSummary


class TraceModelCallResponse(BaseModel):
    attempt: int
    provider: str
    model: str
    status: str
    error_type: str | None = None
    usage: UsageSummary
    latency_ms: int
    created_at: datetime


class TraceDetailResponse(BaseModel):
    trace_id: str
    created_at: datetime
    feature: str
    task_type: str
    routing_policy: str
    risk_level: str
    status: str
    provider: str | None = None
    model: str | None = None
    error_type: str | None = None
    tenant_id: str | None = None
    user_id_hash: str | None = None
    request_metadata: dict | None = None
    input_preview: str | None = None
    output_preview: str | None = None
    validation: ValidationSummary | None = None
    usage: UsageSummary
    fallback: FallbackSummary
    latency_ms: int
    cost_usd: float
    model_calls: list[TraceModelCallResponse]


class CostBreakdownItem(BaseModel):
    key: str
    request_count: int
    success_count: int
    failed_count: int
    total_cost_usd: float
    avg_cost_usd: float


class CostMetricsResponse(BaseModel):
    request_count: int
    success_count: int
    failed_count: int
    total_cost_usd: float
    avg_cost_usd: float
    by_feature: list[CostBreakdownItem]
    by_model: list[CostBreakdownItem]
    by_tenant: list[CostBreakdownItem]
