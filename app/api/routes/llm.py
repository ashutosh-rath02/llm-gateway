from fastapi import APIRouter, Request

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
    return execution_service.execute(payload, trace_id=trace_id)

