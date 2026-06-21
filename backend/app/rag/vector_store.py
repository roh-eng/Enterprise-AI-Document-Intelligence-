"""
FAISS vector store (Tasks 2–4: embeddings → FAISS → retrieval).

Embeds chunks with the sentence-transformers model (Week 4) and stores the
vectors in a FAISS `IndexFlatIP`. Because the vectors are L2-normalised, inner
product == cosine similarity, so a FAISS search returns the most semantically
similar chunks.

The index is persisted to disk per document and cached in memory. Chunk *text*
lives in the database (source of truth); FAISS holds only the vectors, aligned
to the chunk index by insertion order.

Robustness: if FAISS isn't installed, or embeddings fall back to TF-IDF (which
is corpus-dependent and can't be queried independently), retrieval degrades to
an in-memory brute-force cosine search over the chunk texts. Either way the API
behaves identically.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.nlp import embeddings

logger = get_logger(__name__)

# In-memory cache of loaded FAISS indexes, keyed by document id.
_INDEX_CACHE: dict[int, object] = {}


@lru_cache(maxsize=1)
def _faiss():
    """Import faiss lazily; return the module or None."""
    try:
        import faiss

        return faiss
    except Exception as exc:  # pragma: no cover
        logger.warning("faiss not installed (%s); using brute-force retrieval", exc)
        return None


def _use_faiss() -> bool:
    """
    FAISS is usable only with fixed-dimension, query-independent embeddings
    (sentence-transformers). The TF-IDF fallback must re-embed query+chunks
    together, so it can't use a persisted index.
    """
    return _faiss() is not None and embeddings.embedding_backend() == "sentence-transformers"


def _index_path(document_id: int) -> Path:
    base = get_settings().faiss_path
    base.mkdir(parents=True, exist_ok=True)
    return base / f"doc_{document_id}.faiss"


def build_index(document_id: int, chunks: list[str]) -> str:
    """
    Embed `chunks`, build a FAISS index, persist it, and cache it.

    Returns the backend name actually used ("faiss" or "brute-force").
    """
    if not chunks:
        return "empty"

    if not _use_faiss():
        # Nothing to persist; retrieval will brute-force over chunk texts.
        _INDEX_CACHE.pop(document_id, None)
        return "brute-force"

    faiss = _faiss()
    vectors = embeddings.embed_texts(chunks).astype("float32")
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product on normalised vecs = cosine
    index.add(vectors)

    path = _index_path(document_id)
    faiss.write_index(index, str(path))
    _INDEX_CACHE[document_id] = index
    logger.info("Built FAISS index | doc=%s | chunks=%d | dim=%d", document_id, len(chunks), dim)
    return "faiss"


def _load_index(document_id: int):
    """Load a FAISS index from cache or disk; None if absent."""
    if document_id in _INDEX_CACHE:
        return _INDEX_CACHE[document_id]
    faiss = _faiss()
    path = _index_path(document_id)
    if faiss is not None and path.exists():
        index = faiss.read_index(str(path))
        _INDEX_CACHE[document_id] = index
        return index
    return None


def search(document_id: int, chunks: list[str], query: str, k: int = 4) -> list[tuple[int, float]]:
    """
    Retrieve the top-`k` chunk indices most similar to `query`.

    Returns a list of (chunk_index, similarity) sorted by similarity desc.
    """
    if not chunks:
        return []
    k = min(k, len(chunks))

    if _use_faiss():
        index = _load_index(document_id)
        if index is None:
            build_index(document_id, chunks)
            index = _load_index(document_id)
        query_vec = embeddings.embed_texts([query]).astype("float32")
        scores, idxs = index.search(query_vec, k)
        return [
            (int(i), float(s))
            for i, s in zip(idxs[0], scores[0])
            if i != -1
        ]

    # Brute-force fallback: cosine over all chunks (re-embeds together).
    ranked = embeddings.rank_similar(query, list(enumerate(chunks)))
    return [(int(i), float(s)) for i, s in ranked[:k]]


def delete_index(document_id: int) -> None:
    """Remove a document's FAISS index from cache and disk."""
    _INDEX_CACHE.pop(document_id, None)
    path = _index_path(document_id)
    if path.exists():
        path.unlink()
