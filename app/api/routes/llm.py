from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.security import AuthContext, get_auth_context, scope_execute_payload
from app.core.errors import GatewayError
from app.providers.base import ProviderError
from app.schemas.llm import GatewayExecuteRequest, GatewayExecuteResponse
from app.services.execution import ExecutionService
from app.services.rate_limits import execute_rate_limiter
from app.services.validation import enforce_execute_guardrails

router = APIRouter()
execution_service = ExecutionService()


@router.post("/execute", response_model=GatewayExecuteResponse)
def execute_llm_task(
    payload: GatewayExecuteRequest,
    request: Request,
    auth: AuthContext = Depends(get_auth_context),
) -> GatewayExecuteResponse:
    trace_id = getattr(request.state, "trace_id", None)
    try:
        scoped_payload = scope_execute_payload(payload, auth)
        enforce_execute_guardrails(scoped_payload)
        execute_rate_limiter.enforce(auth=auth, request=request)
        return execution_service.execute(scoped_payload, trace_id=trace_id)
    except (ProviderError, GatewayError) as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error_type": exc.error_type,
                "message": str(exc),
                "trace_id": trace_id,
            },
        ) from exc
