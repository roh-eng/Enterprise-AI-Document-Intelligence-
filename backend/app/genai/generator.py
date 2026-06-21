"""
Generation orchestrator.

For each task it: trims input (cost control) → checks a response cache (avoid
paying twice) → calls Gemini if available, parsing structured output → otherwise
runs the offline fallback. Every call is logged with sizes and latency (never
raw content, for privacy). Returns a uniform result dict the API layer maps to a
response schema.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Callable

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.genai import fallback, gemini_client, prompts

logger = get_logger(__name__)

TASKS = ("summary", "explain", "faq", "interview_questions", "action_items", "deadlines")

# Simple in-process response cache: sha256(task|model|text) -> result payload.
# In production this would be Redis/DB with a TTL; the principle is identical —
# never spend tokens regenerating an identical request.
_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_MAX = 256


def _cache_key(task: str, text: str, model: str) -> str:
    digest = hashlib.sha256(f"{task}|{model}|{text}".encode("utf-8")).hexdigest()
    return digest


def _trim_input(text: str) -> str:
    """Cap the characters sent to the LLM (cost control)."""
    limit = get_settings().GENAI_MAX_INPUT_CHARS
    return text[:limit] if len(text) > limit else text


# --- Parsers for Gemini's text output --------------------------------------
def _parse_faq(raw: str) -> list[dict[str, str]]:
    items, question = [], None
    for line in raw.splitlines():
        line = line.strip()
        if line.lower().startswith("q:"):
            question = line[2:].strip()
        elif line.lower().startswith("a:") and question:
            items.append({"question": question, "answer": line[2:].strip()})
            question = None
    return items


def _parse_numbered(raw: str) -> list[str]:
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading numbering / bullets.
        cleaned = line.lstrip("0123456789.-) ").strip()
        if cleaned:
            out.append(cleaned)
    return out


def _parse_bullets(raw: str) -> list[str]:
    if raw.strip().lower() == "none":
        return []
    return [
        line.lstrip("-* ").strip()
        for line in raw.splitlines()
        if line.strip() and line.strip().lower() != "none"
    ]


def _parse_deadlines(raw: str) -> list[dict[str, Any]]:
    if raw.strip().lower() == "none":
        return []
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if "::" in line:
            due, _, desc = line.partition("::")
            out.append({"text": desc.strip(), "due": due.strip()})
    return out


# Maps task -> (output key, Gemini parser, fallback callable).
_HANDLERS: dict[str, tuple[str, Callable[[str], Any], Callable[[str], Any]]] = {
    "summary": ("summary", lambda r: r, fallback.summarize),
    "explain": ("explanation", lambda r: r, fallback.explain),
    "faq": ("faq", _parse_faq, fallback.faq),
    "interview_questions": ("interview_questions", _parse_numbered, fallback.interview_questions),
    "action_items": ("action_items", _parse_bullets, fallback.action_items),
    "deadlines": ("deadlines", _parse_deadlines, fallback.deadlines),
}


def run_task(task: str, text: str) -> dict[str, Any]:
    """Execute a generation task, returning a uniform result payload."""
    if task not in _HANDLERS:
        raise ValueError(f"Unknown task '{task}'. Valid tasks: {', '.join(TASKS)}")
    if not text or not text.strip():
        raise ValueError("Cannot run a generation task on empty text.")

    settings = get_settings()
    text = _trim_input(text)
    output_key, parser, fallback_fn = _HANDLERS[task]
    model_name = settings.GEMINI_MODEL

    # 1) Cache lookup — the cheapest possible "generation".
    key = _cache_key(task, text, model_name)
    if key in _CACHE:
        logger.info("GenAI cache hit | task=%s", task)
        return {**_CACHE[key], "cached": True}

    started = time.perf_counter()

    # 2) Gemini if available, else fallback.
    if gemini_client.is_available():
        try:
            raw = gemini_client.generate(
                prompts.system_instruction(),
                prompts.build_user_prompt(task, text),
                prompts.MAX_OUTPUT_TOKENS[task],
            )
            output, source = parser(raw), "gemini"
        except Exception as exc:
            logger.warning("Gemini failed for task=%s; using fallback: %s", task, exc)
            output, source = fallback_fn(text), "fallback"
    else:
        output, source = fallback_fn(text), "fallback"

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    result = {
        "task": task,
        "model_used": model_name if source == "gemini" else "offline-nlp",
        "source": source,
        "cached": False,
        output_key: output,
    }

    # Log sizes/latency only — never the document or generated content.
    out_size = len(output) if isinstance(output, (list, str)) else 0
    logger.info(
        "GenAI generate | task=%s | source=%s | in_chars=%d | out_size=%d | %.0fms",
        task, source, len(text), out_size, elapsed_ms,
    )

    # 3) Store in the bounded cache.
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))  # evict oldest (FIFO)
    _CACHE[key] = result
    return result
