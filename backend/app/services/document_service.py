"""
Document service — ingestion business logic.

Responsible for turning an uploaded file into a persisted `Document` row:
extract text (TXT / PDF), compute basic stats, and store it against the owning
user. Heavier processing (chunking, embeddings, RAG indexing) is layered on in
later weeks; this service owns the ingestion contract they will build upon.
"""

from __future__ import annotations

import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.models import Document

logger = get_logger(__name__)

# Supported upload types -> human label.
SUPPORTED_CONTENT = {"text/plain": "TXT", "application/pdf": "PDF"}


class UnsupportedFileTypeError(Exception):
    """Raised when an uploaded file is neither TXT nor PDF."""


class TextExtractionError(Exception):
    """Raised when text cannot be extracted from a file."""


def extract_text(filename: str, content_type: str, raw: bytes) -> str:
    """
    Extract plain text from raw file bytes.

    Decides by content type first, falling back to the filename extension
    (browsers don't always send an accurate content type).
    """
    name = filename.lower()
    is_pdf = content_type == "application/pdf" or name.endswith(".pdf")
    is_txt = content_type.startswith("text/") or name.endswith(".txt")

    if is_pdf:
        return _extract_pdf(raw)
    if is_txt:
        return raw.decode("utf-8", errors="ignore").strip()

    raise UnsupportedFileTypeError(
        f"Unsupported file type '{content_type}'. Upload a .pdf or .txt file."
    )


def _extract_pdf(raw: bytes) -> str:
    """Extract text from a PDF using pypdf (imported lazily so TXT-only setups work)."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise TextExtractionError(
            "PDF support requires the 'pypdf' package (pip install pypdf)."
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(raw))
        pages = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(pages).strip()
    except Exception as exc:
        logger.exception("PDF parsing failed")
        raise TextExtractionError(f"Could not parse PDF: {exc}") from exc


def create_document(
    db: Session, *, user_id: int, filename: str, content_type: str, raw: bytes
) -> Document:
    """
    Extract text from an upload and persist a Document owned by `user_id`.

    Raises UnsupportedFileTypeError / TextExtractionError on bad input.
    """
    text = extract_text(filename, content_type, raw)

    document = Document(
        user_id=user_id,
        filename=filename,
        content_type=content_type,
        num_chars=len(text),
        num_chunks=0,  # populated by the RAG pipeline in a later week
        extracted_text=text,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    logger.info(
        "Stored document | id=%s | user=%s | chars=%s | file=%s",
        document.id, user_id, document.num_chars, filename,
    )
    return document


def list_documents_for_user(db: Session, user_id: int) -> list[Document]:
    """Return all documents owned by a user, newest first."""
    stmt = (
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())
