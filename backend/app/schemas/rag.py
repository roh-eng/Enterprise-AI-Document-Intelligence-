"""
Pydantic schemas for the RAG / document-chat endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class IndexResponse(BaseModel):
    """Result of indexing a document into the vector store."""

    document_id: int
    num_chunks: int
    backend: str = Field(description="'faiss' or 'brute-force'.")


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


class SourceCitation(BaseModel):
    chunk_index: int
    text: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    model_used: str
    source: str = Field(description="'gemini' or 'fallback'.")


class ChatMessageOut(BaseModel):
    role: str
    content: str
    sources: list[SourceCitation] = []
    created_at: datetime
