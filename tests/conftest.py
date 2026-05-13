import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_engine, reset_db_caches
from app.main import create_application


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> TestClient:
    database_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database_file.as_posix()}")
    monkeypatch.setenv("DEFAULT_PROVIDER", "mock")
    monkeypatch.setenv("TRACE_PERSISTENCE_ENABLED", "true")

    get_settings.cache_clear()
    reset_db_caches()

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    app = create_application()

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        Base.metadata.drop_all(bind=engine)
        reset_db_caches()
        get_settings.cache_clear()
