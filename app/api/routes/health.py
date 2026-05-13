from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {"service": "llm-gateway", "status": "ok"}


@router.get("/healthz", response_model=HealthResponse, tags=["health"])
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")

