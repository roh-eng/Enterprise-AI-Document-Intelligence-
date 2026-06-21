"""
Pydantic schemas for documents.

  * DocumentRead   — list/summary view shown on the dashboard & upload result.
  * DocumentDetail — extends DocumentRead with the cleaned text body.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    """Metadata view of an uploaded document (no body, keeps lists light)."""

    id: int
    filename: str
    content_type: str
    file_ext: str
    file_size: int
    num_chars: int
    num_chunks: int
    status: str
    category: str | None = None
    category_confidence: float | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetail(DocumentRead):
    """Full document view including the cleaned, extracted text."""

    extracted_text: str
