from app.core.config import get_settings


def worker_settings() -> dict[str, str]:
    settings = get_settings()
    return {
        "redis_url": settings.redis_url,
        "database_url": settings.database_url,
    }

