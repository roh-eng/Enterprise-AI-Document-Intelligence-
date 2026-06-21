"""
ORM models — the database schema expressed as Python classes.

These tables back the platform's persistence layer:
  * Document   — metadata for every uploaded file.
  * Summary    — generated executive summaries (1:1 with a Document).
  * QueryLog   — an audit trail of RAG questions and answers.

Using an ORM (rather than raw SQL) gives us type-safe queries, automatic schema
creation, and a clean migration path from SQLite to PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp (avoids deprecated `datetime.utcnow`)."""
    return datetime.now(timezone.utc)


class Document(Base):
    """Metadata for an uploaded document."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    num_chars: Mapped[int] = mapped_column(Integer, default=0)
    num_chunks: Mapped[int] = mapped_column(Integer, default=0)
    # Full extracted text. In production this would move to object storage.
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships -------------------------------------------------------
    summary: Mapped["Summary | None"] = relationship(
        back_populates="document", cascade="all, delete-orphan", uselist=False
    )
    queries: Mapped[list["QueryLog"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Document id={self.id} filename={self.filename!r}>"


class Summary(Base):
    """An LLM-generated executive summary for a document."""

    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped["Document"] = relationship(back_populates="summary")


class QueryLog(Base):
    """Audit record of a RAG question/answer interaction."""

    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, default="")
    model_used: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped["Document"] = relationship(back_populates="queries")
