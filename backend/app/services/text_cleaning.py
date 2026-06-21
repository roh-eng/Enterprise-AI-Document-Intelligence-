"""
Text cleaning / normalisation.

Raw text extracted from PDFs and DOCX files is noisy: stray control characters,
words split across line breaks with hyphens, inconsistent whitespace, and long
runs of blank lines. Cleaning here gives every downstream consumer (database,
NLP, RAG embeddings) consistent input — garbage in, garbage out.

Kept dependency-free (pure regex) so it is fast and trivially unit-testable.
"""

from __future__ import annotations

import re
import unicodedata

# Control characters except tab/newline — these corrupt text and DB storage.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# A word hyphenated across a line break, e.g. "exam-\nple" -> "example".
_HYPHEN_LINEBREAK = re.compile(r"(\w)-\n(\w)")
# Horizontal whitespace runs (spaces/tabs) — collapse to a single space.
_HSPACE_RUN = re.compile(r"[ \t]+")
# 3+ consecutive newlines -> a single blank line (paragraph break).
_BLANK_LINES = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """
    Normalise extracted text.

    Steps: unicode-normalise -> strip control chars -> normalise newlines ->
    re-join hyphenated line breaks -> collapse whitespace -> trim.

    Returns an empty string for empty/None-ish input (never raises).
    """
    if not text:
        return ""

    # Canonical unicode form so visually-identical chars compare equal.
    text = unicodedata.normalize("NFKC", text)

    # Standardise line endings (Windows/Mac -> Unix).
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Drop control characters that survive extraction.
    text = _CONTROL_CHARS.sub("", text)

    # Re-join words split by a hyphen at a line break.
    text = _HYPHEN_LINEBREAK.sub(r"\1\2", text)

    # Collapse horizontal whitespace, then trim trailing spaces on each line.
    text = _HSPACE_RUN.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))

    # Collapse excessive blank lines and trim the whole string.
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()
