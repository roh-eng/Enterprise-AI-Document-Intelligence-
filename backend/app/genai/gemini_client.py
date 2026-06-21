"""
Thin wrapper around the Google Gemini API (the maintained `google-genai` SDK).

Isolates every Gemini-specific detail (client construction, safety settings,
generation config, retries) so the rest of the app depends only on a simple
`generate(...)` call. If the SDK is missing or no API key is configured,
`is_available()` returns False and callers use the offline fallback — the app
never hard-requires a key.

Note: the older `google-generativeai` package is deprecated; this uses the
current `google-genai` client (`from google import genai`).
"""

from __future__ import annotations

import time
from functools import lru_cache

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class GeminiError(Exception):
    """Raised when a Gemini API call fails after retries."""


@lru_cache(maxsize=1)
def _import_sdk():
    """Import google-genai lazily; return the module or None."""
    try:
        from google import genai
        from google.genai import types

        return genai, types
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.warning("google-genai not installed (%s)", exc)
        return None


def is_available() -> bool:
    """True only when the SDK is importable AND a real API key is configured."""
    return _import_sdk() is not None and get_settings().gemini_enabled


def _safety_settings(types) -> list:
    """Block the most harmful content categories at the API level."""
    threshold = types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    categories = [
        types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    ]
    return [types.SafetySetting(category=c, threshold=threshold) for c in categories]


def generate(system_instruction: str, user_prompt: str, max_output_tokens: int) -> str:
    """
    Call Gemini and return the generated text.

    Retries transient failures up to 3 times with linear backoff. Raises
    GeminiError on definitive failure so the caller can fall back.
    """
    sdk = _import_sdk()
    settings = get_settings()
    if sdk is None or not settings.gemini_enabled:
        raise GeminiError("Gemini is not available (missing SDK or API key).")
    genai, types = sdk

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        max_output_tokens=max_output_tokens,
        temperature=settings.GENAI_TEMPERATURE,
        safety_settings=_safety_settings(types),
    )

    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL, contents=user_prompt, config=config
            )
            return (response.text or "").strip()
        except Exception as exc:  # network/quota/transient errors
            last_exc = exc
            logger.warning("Gemini call failed (attempt %d/3): %s", attempt, exc)
            time.sleep(attempt)  # linear backoff: 1s, 2s

    raise GeminiError(f"Gemini failed after 3 attempts: {last_exc}")
