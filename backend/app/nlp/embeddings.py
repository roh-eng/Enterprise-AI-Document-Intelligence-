"""
Sentence embeddings + cosine similarity (Tasks 7–9).

Embeddings map text to a numeric vector so semantic similarity becomes geometric
proximity. We prefer Sentence-Transformers (dense, semantic embeddings) and fall
back to TF-IDF vectors (lexical embeddings) when the model isn't installed —
both expose the same `embed_texts` interface, and cosine similarity works on
either.

Note on the two backends:
  * Sentence-Transformers produces a fixed-dimension vector *per text*, so texts
    can be embedded independently and compared across calls.
  * TF-IDF vectors depend on a shared vocabulary, so the texts being compared
    must be vectorised *together*. `embed_texts` takes the whole list precisely
    so both backends work through one API.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from app.core.logging_config import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_sentence_model():
    """Load a Sentence-Transformers model, or None if unavailable."""
    try:
        from sentence_transformers import SentenceTransformer

        from app.core.config import get_settings

        model_name = get_settings().EMBEDDING_MODEL
        logger.info("Loading sentence-transformers model: %s", model_name)
        return SentenceTransformer(model_name)
    except Exception as exc:
        logger.warning(
            "sentence-transformers unavailable (%s); using TF-IDF embeddings", exc
        )
        return None


def embedding_backend() -> str:
    """Name of the active embedding backend (for display)."""
    return "sentence-transformers" if _get_sentence_model() else "tf-idf"


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Embed a list of texts into an (n_texts, dim) matrix of L2-normalised vectors.

    Normalising to unit length means the cosine similarity between two vectors is
    simply their dot product.
    """
    if not texts:
        return np.zeros((0, 1), dtype=float)

    model = _get_sentence_model()
    if model is not None:
        vectors = model.encode(texts, normalize_embeddings=True)
        return np.asarray(vectors, dtype=float)

    # TF-IDF fallback — vectorise all texts together to share a vocabulary.
    from sklearn.feature_extraction.text import TfidfVectorizer

    from app.ml.preprocess import preprocess

    vectorizer = TfidfVectorizer(preprocessor=preprocess, lowercase=False)
    matrix = vectorizer.fit_transform(texts).toarray().astype(float)
    # L2-normalise rows (guard against all-zero rows).
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Cosine similarity of two vectors, clamped to [0, 1] for display."""
    denom = float(np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
    if denom == 0.0:
        return 0.0
    sim = float(np.dot(vec_a, vec_b) / denom)
    # TF-IDF vectors are non-negative (sim in [0,1]); dense embeddings can be
    # slightly negative — clamp so the UI always shows a sensible 0..1 value.
    return max(0.0, min(1.0, sim))


def text_similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity between two raw texts."""
    vectors = embed_texts([text_a, text_b])
    if vectors.shape[0] < 2:
        return 0.0
    return cosine_similarity(vectors[0], vectors[1])


def rank_similar(target_text: str, candidates: list[tuple[int, str]]) -> list[tuple[int, float]]:
    """
    Rank candidate documents by similarity to a target text.

    Parameters
    ----------
    target_text : the document to compare against.
    candidates  : list of (document_id, text) pairs.

    Returns a list of (document_id, similarity) sorted by similarity desc.
    """
    if not candidates:
        return []

    texts = [target_text] + [text for _, text in candidates]
    vectors = embed_texts(texts)
    target_vec = vectors[0]
    scored = [
        (doc_id, cosine_similarity(target_vec, vectors[i + 1]))
        for i, (doc_id, _) in enumerate(candidates)
    ]
    scored.sort(key=lambda kv: kv[1], reverse=True)
    return scored
