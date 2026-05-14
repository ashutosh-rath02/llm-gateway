from fastapi import APIRouter, Depends, Query

from app.api.security import AuthContext, get_auth_context, resolve_tenant_scope
from app.repositories.traces import TraceRepository
from app.schemas.trace import CostMetricsResponse, ReliabilityMetricsResponse

router = APIRouter(prefix="/metrics")
trace_repository = TraceRepository()


@router.get("/cost", response_model=CostMetricsResponse)
def get_cost_metrics(
    feature: str | None = Query(default=None),
    model: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    prompt_template_name: str | None = Query(default=None),
    prompt_template_version: str | None = Query(default=None),
    auth: AuthContext = Depends(get_auth_context),
) -> CostMetricsResponse:
    scoped_tenant_id = resolve_tenant_scope(tenant_id, auth)
    return trace_repository.get_cost_metrics(
        feature=feature,
        model=model,
        tenant_id=scoped_tenant_id,
        prompt_template_name=prompt_template_name,
        prompt_template_version=prompt_template_version,
    )


@router.get("/reliability", response_model=ReliabilityMetricsResponse)
def get_reliability_metrics(
    feature: str | None = Query(default=None),
    model: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    prompt_template_name: str | None = Query(default=None),
    prompt_template_version: str | None = Query(default=None),
    auth: AuthContext = Depends(get_auth_context),
) -> ReliabilityMetricsResponse:
    scoped_tenant_id = resolve_tenant_scope(tenant_id, auth)
    return trace_repository.get_reliability_metrics(
        feature=feature,
        model=model,
        tenant_id=scoped_tenant_id,
        prompt_template_name=prompt_template_name,
        prompt_template_version=prompt_template_version,
    )
