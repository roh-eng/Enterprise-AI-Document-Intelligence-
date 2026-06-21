"""
Document chunking (Task 1).

RAG retrieves *chunks*, not whole documents, because (a) embeddings capture a
short passage's meaning far better than a 50-page average, and (b) we can only
fit so much text in the LLM's context window. Chunks overlap so a sentence split
across a boundary still appears whole in at least one chunk.

Uses LangChain's RecursiveCharacterTextSplitter when available (it splits on
paragraph → sentence → word boundaries, preserving structure) and falls back to
a simple word-window splitter otherwise.
"""

from __future__ import annotations

from app.core.logging_config import get_logger

logger = get_logger(__name__)

# ~800 chars ≈ a few sentences: small enough to be specific, large enough for
# context. 120-char overlap keeps boundary sentences intact.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks (LangChain splitter, or fallback)."""
    text = (text or "").strip()
    if not text:
        return []

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_text(text)
    except Exception as exc:  # LangChain missing -> fallback
        logger.warning("LangChain splitter unavailable (%s); using word-window fallback", exc)
        chunks = _fallback_split(text, chunk_size, overlap)

    return [c.strip() for c in chunks if c.strip()]


def _fallback_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Character-window splitter with overlap (no external dependency)."""
    step = max(chunk_size - overlap, 1)
    return [text[i: i + chunk_size] for i in range(0, len(text), step)]
