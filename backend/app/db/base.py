"""
SQLAlchemy declarative base.

Every ORM model inherits from `Base`. Keeping the declarative base in its own
module (separate from the engine/session) prevents circular imports: models
import only `Base`, while the session module imports the models.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class shared by all ORM models."""

    pass
