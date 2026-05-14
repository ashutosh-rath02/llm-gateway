from fastapi import FastAPI

from app.api.router import api_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.trace import TraceMiddleware


def create_application() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(TraceMiddleware)
    app.include_router(health_router)
    app.include_router(dashboard_router)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_application()
