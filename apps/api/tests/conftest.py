import shutil
from collections.abc import Generator
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.storage import LocalDiskStorageProvider, get_storage_provider

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures"
FIXTURE_VIDEO = FIXTURES_DIR / "speech_45s.mp4"

_TEST_DB_NAME = "clip_engine_test"


def _admin_connection_url() -> str:
    base = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    return base.rsplit("/", 1)[0] + "/postgres"


def _test_database_url() -> str:
    base = settings.database_url.replace("postgresql+psycopg://", "postgresql+psycopg://")
    return base.rsplit("/", 1)[0] + f"/{_TEST_DB_NAME}"


@pytest.fixture(scope="session", autouse=True)
def _test_database() -> Generator[None, None, None]:
    with psycopg.connect(_admin_connection_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (_TEST_DB_NAME,))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')

    engine = create_engine(_test_database_url())
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    yield


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "storage"


@pytest.fixture
def client(
    storage_root: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    engine = create_engine(_test_database_url())
    for table in reversed(Base.metadata.sorted_tables):
        with engine.begin() as conn:
            conn.execute(table.delete())

    TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator:
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    storage_provider = LocalDiskStorageProvider(storage_root)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_provider] = lambda: storage_provider

    # The YouTube-download background task resolves its DB session and
    # storage provider directly (it runs outside a request scope, so
    # FastAPI's dependency_overrides above don't reach it). Patch the
    # names it looks up in app.api.sources so tests exercise the same
    # test database and temp storage as the rest of the request.
    monkeypatch.setattr("app.api.sources.SessionLocal", TestSessionLocal)
    monkeypatch.setattr("app.api.sources.get_storage_provider", lambda: storage_provider)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()
    shutil.rmtree(storage_root, ignore_errors=True)
