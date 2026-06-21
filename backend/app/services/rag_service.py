"""
RAG service — document indexing, chat, and conversation history.

Owns the database side of RAG: persisting chunks, recording chat turns, and
enforcing document ownership. Routes call these functions; the heavy lifting
(embedding, retrieval, generation) lives in app.rag.*.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.models import ChatMessage, DocumentChunk
from app.rag import chunking, pipeline, vector_store
from app.services import document_service

logger = get_logger(__name__)


def get_chunks(db: Session, document_id: int) -> list[str]:
    """Return a document's chunk texts in order."""
    stmt = (
        select(DocumentChunk.text)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return list(db.execute(stmt).scalars().all())


def index_document(db: Session, user_id: int, document_id: int) -> dict[str, Any]:
    """
    Chunk a document, persist the chunks, and build its FAISS index.

    Idempotent: re-indexing replaces existing chunks and rebuilds the index.
    """
    document = document_service.get_document(db, user_id, document_id)

    # Clear any previous chunks/index for a clean rebuild.
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    vector_store.delete_index(document_id)

    chunks = chunking.split_text(document.extracted_text)
    for i, text in enumerate(chunks):
        db.add(DocumentChunk(document_id=document_id, chunk_index=i, text=text))
    document.num_chunks = len(chunks)
    db.commit()

    backend = vector_store.build_index(document_id, chunks)
    logger.info("Indexed document | id=%s | chunks=%d | backend=%s", document_id, len(chunks), backend)
    return {"document_id": document_id, "num_chunks": len(chunks), "backend": backend}


def _ensure_indexed(db: Session, user_id: int, document_id: int) -> list[str]:
    """Return chunks, indexing the document on first use."""
    chunks = get_chunks(db, document_id)
    if not chunks:
        index_document(db, user_id, document_id)
        chunks = get_chunks(db, document_id)
    return chunks


def chat(db: Session, user_id: int, document_id: int, question: str) -> dict[str, Any]:
    """
    Answer a question about a document and record the conversation turns.

    Auto-indexes the document if it hasn't been indexed yet.
    """
    # Ownership is enforced by get_document inside _ensure_indexed/index_document.
    chunks = _ensure_indexed(db, user_id, document_id)
    result = pipeline.answer_question(document_id, chunks, question)

    sources = [
        {"chunk_index": s.chunk_index, "text": s.text, "score": s.score}
        for s in result.sources
    ]

    # Persist both turns of the conversation.
    db.add(ChatMessage(document_id=document_id, user_id=user_id, role="user", content=question))
    db.add(ChatMessage(
        document_id=document_id, user_id=user_id, role="assistant",
        content=result.answer, sources=json.dumps(sources),
    ))
    db.commit()

    return {
        "answer": result.answer,
        "sources": sources,
        "model_used": result.model_used,
        "source": result.source,
    }


def history(db: Session, user_id: int, document_id: int) -> list[dict[str, Any]]:
    """Return the conversation history for a document (oldest first)."""
    document_service.get_document(db, user_id, document_id)  # ownership check
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.document_id == document_id, ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
    )
    messages = db.execute(stmt).scalars().all()
    return [
        {
            "role": m.role,
            "content": m.content,
            "sources": json.loads(m.sources) if m.sources else [],
            "created_at": m.created_at,
        }
        for m in messages
    ]


def clear_history(db: Session, user_id: int, document_id: int) -> None:
    """Delete the conversation history for a document."""
    document_service.get_document(db, user_id, document_id)  # ownership check
    db.execute(
        delete(ChatMessage).where(
            ChatMessage.document_id == document_id, ChatMessage.user_id == user_id
        )
    )
    db.commit()
