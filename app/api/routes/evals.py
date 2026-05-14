from fastapi import APIRouter

from app.repositories.traces import TraceRepository
from app.schemas.evals import EvalExportRequest, EvalExportResponse

router = APIRouter(prefix="/evals")
trace_repository = TraceRepository()


@router.post("/export", response_model=EvalExportResponse)
def export_eval_dataset(payload: EvalExportRequest) -> EvalExportResponse:
    return trace_repository.export_eval_dataset(payload)
