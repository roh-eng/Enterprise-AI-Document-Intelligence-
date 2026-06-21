"""
Pytest fixtures.

Provides a `client` fixture backed by an isolated in-memory SQLite database, so
tests never touch the real `data/app.db`. We override the `get_db` dependency to
hand endpoints a session bound to the test engine.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture(autouse=True)
def _clear_genai_cache():
    """Clear the GenAI response cache so tests don't see each other's results."""
    from app.genai import generator

    generator._CACHE.clear()
    yield
    generator._CACHE.clear()


@pytest.fixture(autouse=True)
def _isolated_upload_dir(tmp_path):
    """
    Redirect file storage to a per-test temp directory so tests never pollute
    the real data/uploads folder. Restored afterwards.
    """
    settings = get_settings()
    original = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = str(tmp_path / "uploads")
    yield
    settings.UPLOAD_DIR = original


@pytest.fixture()
def client():
    """A TestClient wired to a fresh in-memory database per test."""
    # StaticPool keeps a single shared connection so the in-memory DB persists
    # across requests within one test.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    # No `with` block: we skip lifespan startup so the real DB is never created.
    yield TestClient(app)
    app.dependency_overrides.clear()
