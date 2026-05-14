from fastapi import APIRouter, Depends, HTTPException

from app.api.security import AuthContext, get_auth_context, require_trace_access
from app.repositories.traces import TraceRepository
from app.schemas.trace import TraceDetailResponse

router = APIRouter(prefix="/traces")
trace_repository = TraceRepository()


@router.get("/{trace_id}", response_model=TraceDetailResponse)
def get_trace(
    trace_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> TraceDetailResponse:
    trace = trace_repository.get_trace_detail(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail={"message": "Trace not found."})
    require_trace_access(trace, auth)
    return trace
