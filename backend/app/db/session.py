"""
Database engine and session management.

Exposes:
  * `engine`        — the SQLAlchemy engine bound to DATABASE_URL.
  * `SessionLocal`  — a configured session factory.
  * `get_db`        — a FastAPI dependency yielding a scoped session.
  * `init_db`       — creates all tables (dev convenience; use Alembic in prod).
"""

from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.db.base import Base
# Import models so they register with `Base.metadata` before `create_all`.
from app.db import models  # noqa: F401

logger = get_logger(__name__)
settings = get_settings()

# Ensure the SQLite parent directory exists *before* the engine opens it,
# otherwise sqlite raises "unable to open database file".
if settings.sqlite_path is not None:
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

# SQLite needs `check_same_thread=False` to be used across FastAPI threads.
_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(
    settings.database_url,  # resolved (absolute for SQLite) URL
    connect_args=_connect_args,
    pool_pre_ping=True,  # transparently recycle dead connections
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def init_db() -> None:
    """
    Create all tables defined on `Base.metadata`.

    For local/dev use only. A production deployment should manage schema
    changes through Alembic migrations rather than `create_all`.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialised | url=%s", settings.database_url)
    except Exception:
        logger.exception("Failed to initialise the database")
        raise


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and guarantees cleanup.

    Used as:  `def endpoint(db: Session = Depends(get_db)): ...`
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
