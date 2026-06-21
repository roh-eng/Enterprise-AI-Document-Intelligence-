"""
RAG pipeline (Tasks 5, 7, 9): retrieve → build context → generate grounded answer.

Ties together chunking, the FAISS vector store, and the Gemini client. When
Gemini is unavailable it falls back to an extractive answer drawn from the
top-retrieved chunk, so chat always responds — and always with citations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.logging_config import get_logger
from app.genai import gemini_client
from app.rag import prompts, vector_store

logger = get_logger(__name__)

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Source:
    """A retrieved passage used to answer a question."""

    chunk_index: int
    text: str
    score: float


@dataclass
class Answer:
    """A grounded answer plus the sources it cites."""

    answer: str
    sources: list[Source]
    model_used: str
    source: str  # "gemini" | "fallback"


def retrieve(document_id: int, chunks: list[str], question: str, k: int = 4) -> list[Source]:
    """Retrieve the top-k most relevant chunks for a question."""
    hits = vector_store.search(document_id, chunks, question, k=k)
    return [Source(chunk_index=i, text=chunks[i], score=round(s, 4)) for i, s in hits]


def build_context(sources: list[Source]) -> str:
    """Format retrieved passages into a numbered context block for the prompt."""
    return "\n\n".join(f"[{n}] {s.text}" for n, s in enumerate(sources, start=1))


def answer_question(document_id: int, chunks: list[str], question: str, k: int = 4) -> Answer:
    """Run the full RAG step for one question."""
    sources = retrieve(document_id, chunks, question, k=k)
    if not sources:
        return Answer(
            answer="I could not find that in the document.",
            sources=[], model_used="none", source="fallback",
        )

    context = build_context(sources)

    if gemini_client.is_available():
        try:
            text = gemini_client.generate(
                prompts.system_instruction(),
                prompts.build_prompt(context, question),
                max_output_tokens=512,
            )
            from app.core.config import get_settings

            return Answer(text, sources, get_settings().GEMINI_MODEL, "gemini")
        except Exception as exc:
            logger.warning("Gemini RAG generation failed; using extractive fallback: %s", exc)

    # Offline fallback: extract the most query-relevant sentences from the top
    # passage and cite it. Grounded, deterministic, free.
    return Answer(_extractive_answer(question, sources), sources, "offline-extractive", "fallback")


def _extractive_answer(question: str, sources: list[Source]) -> str:
    """Compose an answer from the best passage's most relevant sentences."""
    q_terms = set(re.findall(r"[a-zA-Z]{3,}", question.lower()))
    best = sources[0]
    sentences = [s for s in _SENT_SPLIT.split(best.text) if s.strip()]
    ranked = sorted(
        sentences,
        key=lambda s: len(q_terms & set(re.findall(r"[a-zA-Z]{3,}", s.lower()))),
        reverse=True,
    )
    snippet = " ".join(ranked[:2]).strip() if ranked else best.text
    return f"{snippet} [1]"
