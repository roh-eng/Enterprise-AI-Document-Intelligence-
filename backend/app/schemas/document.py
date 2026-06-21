"""
Pydantic schemas for documents.

`DocumentRead` is the serialised view of a `Document` ORM row returned to the
frontend (e.g. on the dashboard list and after an upload).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    """Public representation of an uploaded document."""

    id: int
    filename: str
    content_type: str
    num_chars: int
    num_chunks: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
