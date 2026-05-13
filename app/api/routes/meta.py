from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/meta")
def metadata() -> dict[str, str]:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "default_provider": settings.default_provider,
        "default_model": settings.default_model,
    }

