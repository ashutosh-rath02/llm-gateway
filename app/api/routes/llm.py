from fastapi import APIRouter, HTTPException, Request

from app.providers.base import ProviderError
from app.schemas.llm import GatewayExecuteRequest, GatewayExecuteResponse
from app.services.execution import ExecutionService

router = APIRouter()
execution_service = ExecutionService()


@router.post("/execute", response_model=GatewayExecuteResponse)
def execute_llm_task(
    payload: GatewayExecuteRequest,
    request: Request,
) -> GatewayExecuteResponse:
    trace_id = getattr(request.state, "trace_id", None)
    try:
        return execution_service.execute(payload, trace_id=trace_id)
    except ProviderError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error_type": exc.error_type,
                "message": str(exc),
                "trace_id": trace_id,
            },
        ) from exc
