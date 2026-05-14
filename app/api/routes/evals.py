from fastapi import APIRouter, Depends

from app.api.security import AuthContext, get_auth_context, scope_eval_export_request
from app.repositories.traces import TraceRepository
from app.schemas.evals import EvalExportRequest, EvalExportResponse

router = APIRouter(prefix="/evals")
trace_repository = TraceRepository()


@router.post("/export", response_model=EvalExportResponse)
def export_eval_dataset(
    payload: EvalExportRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> EvalExportResponse:
    scoped_payload = scope_eval_export_request(payload, auth)
    return trace_repository.export_eval_dataset(scoped_payload)
