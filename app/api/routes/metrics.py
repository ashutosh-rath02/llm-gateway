from fastapi import APIRouter, Query

from app.repositories.traces import TraceRepository
from app.schemas.trace import CostMetricsResponse

router = APIRouter(prefix="/metrics")
trace_repository = TraceRepository()


@router.get("/cost", response_model=CostMetricsResponse)
def get_cost_metrics(
    feature: str | None = Query(default=None),
    model: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
) -> CostMetricsResponse:
    return trace_repository.get_cost_metrics(
        feature=feature,
        model=model,
        tenant_id=tenant_id,
    )
