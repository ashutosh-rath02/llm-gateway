from fastapi import APIRouter

from app.api.routes.llm import router as llm_router
from app.api.routes.meta import router as meta_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.traces import router as traces_router

api_router = APIRouter()
api_router.include_router(meta_router, tags=["meta"])
api_router.include_router(llm_router, prefix="/llm", tags=["llm"])
api_router.include_router(traces_router, tags=["traces"])
api_router.include_router(metrics_router, tags=["metrics"])
