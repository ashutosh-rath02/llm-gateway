from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.llm import FallbackSummary, UsageSummary


class EvalExportRequest(BaseModel):
    feature: str | None = None
    task_type: str | None = None
    model: str | None = None
    status: str | None = None
    tenant_id: str | None = None
    fallback_used: bool | None = None
    prompt_template_name: str | None = None
    prompt_template_version: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)


class EvalDatasetAttempt(BaseModel):
    attempt: int
    attempt_kind: str
    provider: str
    model: str
    status: str
    error_type: str | None = None
    usage: UsageSummary
    latency_ms: int
    created_at: datetime


class EvalDatasetItem(BaseModel):
    trace_id: str
    created_at: datetime
    feature: str
    task_type: str
    provider: str | None = None
    model: str | None = None
    status: str
    input: str | None = None
    output: Any | None = None
    expected: Any | None = None
    prompt_template_name: str | None = None
    prompt_template_version: str | None = None
    tenant_id: str | None = None
    user_id_hash: str | None = None
    request_metadata: dict | None = None
    schema_valid: bool | None = None
    business_rules_valid: bool | None = None
    fallback: FallbackSummary
    usage: UsageSummary
    latency_ms: int
    cost_usd: float
    model_calls: list[EvalDatasetAttempt]


class EvalExportResponse(BaseModel):
    item_count: int
    filters: dict[str, Any]
    items: list[EvalDatasetItem]
