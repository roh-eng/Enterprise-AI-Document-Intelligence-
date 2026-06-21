"""
NLP service — bridges the NLP pipeline/embeddings with the document domain.

Keeps routes thin: they call these functions, which own ownership checks and the
assembly of document-aware results (e.g. similarity against a user's own corpus).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.nlp import embeddings, pipeline
from app.services import document_service

logger = get_logger(__name__)

# Upper bound on text analysed in one call — guards latency and memory against
# pathologically large inputs (parallels the GenAI input cap).
_MAX_ANALYZE_CHARS = 50_000


def analyze_text(text: str, top_keywords: int = 10) -> dict[str, Any]:
    """Run the full NLP analysis over arbitrary text (input length-capped)."""
    return pipeline.analyze_text(text[:_MAX_ANALYZE_CHARS], top_keywords=top_keywords)


def analyze_document(db: Session, user_id: int, document_id: int) -> dict[str, Any]:
    """Run NLP analysis over a stored document the user owns."""
    document = document_service.get_document(db, user_id, document_id)
    return pipeline.analyze_text(document.extracted_text)


def text_similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity between two raw texts."""
    return embeddings.text_similarity(text_a, text_b)


def similar_documents(
    db: Session, user_id: int, document_id: int, top_k: int = 5
) -> list[dict[str, Any]]:
    """
    Find the user's documents most similar to the target document.

    Compares the target against every *other* document the user owns and returns
    the top matches with their cosine similarity.
    """
    target = document_service.get_document(db, user_id, document_id)

    # Fetch the corpus once and reuse it for both ranking and name lookup.
    corpus = document_service.list_documents_for_user(db, user_id)
    id_to_name = {d.id: d.filename for d in corpus}
    others = [
        (d.id, d.extracted_text)
        for d in corpus
        if d.id != document_id and d.extracted_text.strip()
    ]
    if not others:
        return []

    ranked = embeddings.rank_similar(target.extracted_text, others)[:top_k]
    return [
        {"document_id": doc_id, "filename": id_to_name.get(doc_id, "?"), "similarity": round(sim, 4)}
        for doc_id, sim in ranked
    ]
