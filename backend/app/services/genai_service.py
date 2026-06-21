"""
GenAI service — bridges the generation engine with the document domain.

Resolves the input (raw text or an owned document), runs the task, and — for
executive summaries of stored documents — persists the result into the
`summaries` table (the Summary model created in Week 1), so summaries are
reusable without re-generating.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.models import Summary
from app.genai import generator
from app.services import document_service

logger = get_logger(__name__)


def generate(
    db: Session,
    user_id: int,
    task: str,
    text: str | None = None,
    document_id: int | None = None,
) -> dict[str, Any]:
    """
    Run a generation task on raw text or an owned document.

    Raises DocumentNotFoundError (from document_service) if the document isn't
    owned by the user, ValueError for bad input.
    """
    if document_id is not None:
        document = document_service.get_document(db, user_id, document_id)
        source_text = document.extracted_text
    else:
        source_text = text or ""

    result = generator.run_task(task, source_text)

    # Persist executive summaries of stored documents for reuse.
    if task == "summary" and document_id is not None and not result.get("cached"):
        _persist_summary(db, document_id, result["summary"], result["model_used"])

    return result


def _persist_summary(db: Session, document_id: int, content: str, model_used: str) -> None:
    """Upsert the document's executive summary row."""
    existing = (
        db.query(Summary).filter(Summary.document_id == document_id).one_or_none()
    )
    if existing is None:
        db.add(Summary(document_id=document_id, content=content, model_used=model_used))
    else:
        existing.content = content
        existing.model_used = model_used
    db.commit()
    logger.info("Persisted summary | document_id=%s | model=%s", document_id, model_used)
