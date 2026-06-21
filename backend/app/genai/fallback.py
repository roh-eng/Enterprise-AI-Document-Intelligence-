"""
Offline fallback generators.

When Gemini is unavailable (no API key / no network), these deterministic,
dependency-light functions produce a useful approximation of each task using
classic NLP: extractive summarisation, keyword/entity mining, and regex
extraction. They guarantee the feature always returns something sensible — and
they double as a transparent, free baseline.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from app.ml.preprocess import preprocess
from app.nlp import pipeline

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Verbs/markers that typically introduce an action item.
_ACTION_MARKERS = re.compile(
    r"\b(must|should|shall|need to|needs to|please|ensure|submit|complete|review|"
    r"send|provide|prepare|schedule|follow up|action required|deadline|due|"
    r"required to|responsible for|to do|finalize|finalise|approve|confirm)\b",
    re.IGNORECASE,
)

# Date / deadline patterns.
_MONTHS = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
_DATE_PATTERNS = [
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
    re.compile(rf"\b{_MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b", re.IGNORECASE),
    re.compile(r"\bwithin\s+\d+\s+(?:day|days|week|weeks|month|months)\b", re.IGNORECASE),
    re.compile(r"\bby\s+(?:eod|tomorrow|end of (?:day|week|month)|next\s+\w+|\w+day)\b", re.IGNORECASE),
]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text.strip()) if s.strip()]


def summarize(text: str, max_sentences: int = 5) -> str:
    """Extractive summary: rank sentences by summed TF-IDF of their terms."""
    sentences = _sentences(text)
    if not sentences:
        return "_No readable text to summarise._"
    if len(sentences) <= max_sentences:
        bullets = "\n".join(f"- {s}" for s in sentences)
        return f"**TL;DR** {sentences[0]}\n\n{bullets}"

    # IDF across sentences.
    tokenized = [preprocess(s).split() for s in sentences]
    df: Counter = Counter()
    for toks in tokenized:
        df.update(set(toks))
    n = len(sentences)
    idf = {t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()}

    scores = [
        (sum(idf.get(t, 0.0) for t in toks) / math.sqrt(len(toks)) if toks else 0.0)
        for toks in tokenized
    ]
    top_idx = sorted(range(n), key=lambda i: scores[i], reverse=True)[:max_sentences]
    top_idx.sort()  # preserve original order
    bullets = "\n".join(f"- {sentences[i]}" for i in top_idx)
    return f"**TL;DR** {sentences[top_idx[0]]}\n\n{bullets}"


def explain(text: str) -> str:
    """Plain-language description from stats, keywords, and entities."""
    sentences = _sentences(text)
    words = len(text.split())
    keywords = [k["term"] for k in pipeline.extract_keywords(text, 6)]
    entities = pipeline.extract_entities(text)[:5]
    ent_str = ", ".join(f"{e['text']} ({e['label']})" for e in entities) or "none detected"
    topic = ", ".join(keywords[:5]) or "general content"
    opening = sentences[0] if sentences else ""
    return (
        f"This document contains roughly {words:,} words across "
        f"{len(sentences)} sentences. Its central topics appear to be: {topic}. "
        f"Notable entities mentioned include: {ent_str}.\n\n"
        f"It opens with: \"{opening}\" Based on the prominent terms, the document "
        f"is primarily concerned with the subjects listed above. (Generated "
        f"offline via extractive analysis — configure a Gemini API key for a "
        f"full natural-language explanation.)"
    )


def faq(text: str, n: int = 5) -> list[dict[str, str]]:
    """Build Q&A pairs by pairing top keywords with the sentence that mentions them."""
    sentences = _sentences(text)
    keywords = [k["term"] for k in pipeline.extract_keywords(text, n * 2)]
    items: list[dict[str, str]] = []
    used: set[int] = set()
    for kw in keywords:
        for i, sent in enumerate(sentences):
            if i not in used and kw.split()[0].lower() in sent.lower():
                items.append({
                    "question": f"What does the document say about {kw}?",
                    "answer": sent,
                })
                used.add(i)
                break
        if len(items) >= n:
            break
    if not items and sentences:
        items.append({"question": "What is this document about?", "answer": sentences[0]})
    return items


def interview_questions(text: str) -> list[str]:
    """Template insightful questions around the document's key topics."""
    keywords = [k["term"] for k in pipeline.extract_keywords(text, 5)] or ["the main topic"]
    kw = keywords + ["the subject matter"] * 4  # pad so indexing is safe
    return [
        "What is the primary purpose of this document?",
        f"Can you summarise the key points regarding {kw[0]}?",
        f"How does {kw[1]} relate to {kw[2]}?",
        "What are the main risks, implications, or limitations mentioned?",
        f"Why is {kw[3]} significant in this context?",
        "What action or decision does this document ultimately call for?",
    ]


def action_items(text: str) -> list[str]:
    """Return sentences that look like tasks/action items."""
    return [s for s in _sentences(text) if _ACTION_MARKERS.search(s)]


def deadlines(text: str) -> list[dict[str, Any]]:
    """Extract sentences containing dates/deadlines plus the matched date string."""
    out: list[dict[str, Any]] = []
    for sent in _sentences(text):
        for pattern in _DATE_PATTERNS:
            match = pattern.search(sent)
            if match:
                out.append({"text": sent, "due": match.group(0)})
                break
    return out
