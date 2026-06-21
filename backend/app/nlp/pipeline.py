"""
Core NLP pipeline: tokenization, stopword removal, lemmatization, NER, keyword
extraction, and sentiment analysis.

Design principle — *graceful degradation*. Each technique prefers a real NLP
library (spaCy for tokenization/lemmatization/NER, NLTK VADER for sentiment) but
falls back to a transparent, dependency-light implementation when the library or
its model data is unavailable. The public functions therefore behave identically
to callers whether or not the heavy models are installed; only quality differs.

All heavy resources are loaded lazily and cached, so importing this module is
cheap and the first call pays the (one-time) model-load cost.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from app.core.logging_config import get_logger
from app.ml.preprocess import STOPWORDS

logger = get_logger(__name__)

# Token = run of letters/apostrophes. Used by the regex fallback tokenizer.
_WORD_RE = re.compile(r"[A-Za-z']+")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Minimal lexicons for the fallback sentiment analyser.
_POSITIVE = {
    "good", "great", "excellent", "amazing", "love", "loved", "happy", "best",
    "wonderful", "fantastic", "positive", "success", "successful", "improve",
    "improved", "benefit", "recommend", "satisfied", "efficient", "helpful",
}
_NEGATIVE = {
    "bad", "terrible", "awful", "hate", "poor", "worst", "negative", "fail",
    "failed", "failure", "problem", "issue", "delay", "delayed", "loss",
    "broken", "difficult", "concern", "risk", "disappointed", "unfortunately",
}
_NEGATORS = {"not", "no", "never", "without", "hardly"}


# ---------------------------------------------------------------------------
# Lazy resource loaders
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _get_spacy():
    """Load the spaCy pipeline, or None if unavailable (logged once)."""
    try:
        import spacy

        from app.core.config import get_settings

        return spacy.load(get_settings().SPACY_MODEL)
    except Exception as exc:  # ImportError or OSError (model not downloaded)
        logger.warning("spaCy model unavailable (%s); using regex NLP fallbacks", exc)
        return None


@lru_cache(maxsize=1)
def _get_lemmatizer():
    """Return an NLTK WordNet lemmatizer, or None if its data is missing."""
    try:
        from nltk.stem import WordNetLemmatizer

        lem = WordNetLemmatizer()
        lem.lemmatize("running", pos="v")  # force WordNet load (raises if absent)
        return lem
    except Exception as exc:
        logger.warning("NLTK lemmatizer unavailable (%s); using suffix fallback", exc)
        return None


@lru_cache(maxsize=1)
def _get_vader():
    """Return an NLTK VADER analyser, or None if its lexicon is missing."""
    try:
        from nltk.sentiment import SentimentIntensityAnalyzer

        return SentimentIntensityAnalyzer()
    except Exception as exc:
        logger.warning("NLTK VADER unavailable (%s); using lexicon fallback", exc)
        return None


def active_engines() -> dict[str, str]:
    """Report which backend is actually serving each technique (for the UI)."""
    return {
        "tokenizer": "spaCy" if _get_spacy() else "regex",
        "lemmatizer": "spaCy" if _get_spacy() else ("NLTK" if _get_lemmatizer() else "rule-based"),
        "ner": "spaCy" if _get_spacy() else "regex-heuristic",
        "sentiment": "NLTK-VADER" if _get_vader() else "lexicon",
    }


# ---------------------------------------------------------------------------
# 1. Tokenization
# ---------------------------------------------------------------------------
def tokenize(text: str) -> list[str]:
    """Split text into word tokens (spaCy tokenizer, or regex fallback)."""
    nlp = _get_spacy()
    if nlp is not None:
        return [t.text for t in nlp.tokenizer(text) if not t.is_space and t.text.strip()]
    return _WORD_RE.findall(text)


# ---------------------------------------------------------------------------
# 2. Stopword removal
# ---------------------------------------------------------------------------
def remove_stopwords(tokens: list[str]) -> list[str]:
    """Drop stopwords and pure punctuation; keep alphabetic content words."""
    return [t for t in tokens if t.lower() not in STOPWORDS and t.isalpha()]


# ---------------------------------------------------------------------------
# 3. Lemmatization
# ---------------------------------------------------------------------------
def _rule_lemmatize(token: str) -> str:
    """Tiny suffix-stripping lemmatizer used when no library is available."""
    low = token.lower()
    for suffix, repl in (("ies", "y"), ("sses", "ss"), ("ing", ""), ("ed", ""), ("s", "")):
        if low.endswith(suffix) and len(low) - len(suffix) >= 3:
            return low[: len(low) - len(suffix)] + repl
    return low


def lemmatize(tokens: list[str]) -> list[str]:
    """Reduce tokens to base form (spaCy > NLTK > rule-based fallback)."""
    nlp = _get_spacy()
    if nlp is not None:
        doc = nlp(" ".join(tokens))
        return [t.lemma_.lower() for t in doc if t.lemma_.strip()]
    lem = _get_lemmatizer()
    if lem is not None:
        return [lem.lemmatize(t.lower()) for t in tokens]
    return [_rule_lemmatize(t) for t in tokens]


# ---------------------------------------------------------------------------
# 4. Named Entity Recognition
# ---------------------------------------------------------------------------
# Regex patterns for the fallback NER (used only when spaCy is unavailable).
_NER_PATTERNS = [
    ("MONEY", re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("DATE", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")),
    ("PERCENT", re.compile(r"\b\d+(?:\.\d+)?\s?%")),
    # Sequences of Capitalised Words -> candidate proper nouns (ORG/PERSON).
    ("PROPN", re.compile(r"\b(?:[A-Z][a-z]+)(?:\s+[A-Z][a-z]+){1,3}\b")),
]


def extract_entities(text: str) -> list[dict[str, str]]:
    """
    Extract named entities as [{"text": ..., "label": ...}].

    spaCy provides real typed entities (PERSON, ORG, GPE, DATE, MONEY, ...);
    the fallback uses regex/capitalisation heuristics.
    """
    nlp = _get_spacy()
    if nlp is not None:
        doc = nlp(text)
        seen: set[tuple[str, str]] = set()
        out: list[dict[str, str]] = []
        for ent in doc.ents:
            key = (ent.text.strip(), ent.label_)
            if key not in seen and ent.text.strip():
                seen.add(key)
                out.append({"text": ent.text.strip(), "label": ent.label_})
        return out

    # Fallback: regex heuristics.
    found: list[dict[str, str]] = []
    seen_text: set[str] = set()
    for label, pattern in _NER_PATTERNS:
        for match in pattern.findall(text):
            value = match.strip()
            if value and value not in seen_text:
                seen_text.add(value)
                found.append({"text": value, "label": label})
    return found


# ---------------------------------------------------------------------------
# 5 & 6. Keyword extraction via TF-IDF
# ---------------------------------------------------------------------------
def extract_keywords(text: str, top_k: int = 10) -> list[dict[str, Any]]:
    """
    Extract the top keywords/keyphrases by TF-IDF.

    Each sentence is treated as a mini-document; a term's score is its summed
    TF-IDF across sentences. This surfaces terms that are frequent yet
    distinctive — the essence of keyword extraction. Falls back to frequency
    counting when there are too few sentences for IDF to be meaningful.
    """
    from app.ml.preprocess import preprocess

    sentences = [s for s in _SENT_SPLIT_RE.split(text.strip()) if s.strip()]
    if len(sentences) < 2:
        # Not enough documents for IDF — rank by raw frequency instead.
        tokens = remove_stopwords(tokenize(text))
        from collections import Counter

        counts = Counter(t.lower() for t in tokens)
        return [
            {"term": term, "score": float(count)}
            for term, count in counts.most_common(top_k)
        ]

    from sklearn.feature_extraction.text import TfidfVectorizer

    vectorizer = TfidfVectorizer(
        preprocessor=preprocess, ngram_range=(1, 2), lowercase=False
    )
    try:
        matrix = vectorizer.fit_transform(sentences)
    except ValueError:
        return []  # empty vocabulary after preprocessing
    scores = matrix.sum(axis=0).A1  # summed TF-IDF per term across sentences
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(terms, scores), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [{"term": str(term), "score": round(float(score), 4)} for term, score in ranked]


# ---------------------------------------------------------------------------
# 10. Sentiment analysis
# ---------------------------------------------------------------------------
def analyze_sentiment(text: str) -> dict[str, Any]:
    """
    Classify sentiment as Positive / Neutral / Negative with a [-1, 1] score.

    Uses NLTK VADER (tuned for general/social text) when available; otherwise a
    lexicon heuristic with simple negation handling.
    """
    clean = (text or "").strip()
    if not clean:
        return {"label": "Neutral", "score": 0.0, "engine": "none"}

    vader = _get_vader()
    if vader is not None:
        score = float(vader.polarity_scores(clean)["compound"])
        engine = "NLTK-VADER"
    else:
        score, engine = _lexicon_sentiment(clean)

    label = "Positive" if score > 0.15 else "Negative" if score < -0.15 else "Neutral"
    return {"label": label, "score": round(score, 4), "engine": engine}


def _lexicon_sentiment(text: str) -> tuple[float, str]:
    """Lexicon polarity in [-1, 1] with naive negation flipping."""
    tokens = _WORD_RE.findall(text.lower())
    score = 0
    for i, tok in enumerate(tokens):
        weight = 1 if tok in _POSITIVE else -1 if tok in _NEGATIVE else 0
        if weight and any(w in _NEGATORS for w in tokens[max(0, i - 2): i]):
            weight = -weight
        score += weight
    norm = max(-1.0, min(1.0, score / max(len(tokens) ** 0.5, 1.0)))
    return norm, "lexicon"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def analyze_text(text: str, top_keywords: int = 10) -> dict[str, Any]:
    """Run the full NLP pipeline over `text` and return a structured report."""
    if not text or not text.strip():
        raise ValueError("Cannot analyse empty text.")

    tokens = tokenize(text)
    content_tokens = remove_stopwords(tokens)
    lemmas = lemmatize(content_tokens)
    sentences = [s for s in _SENT_SPLIT_RE.split(text.strip()) if s.strip()]

    return {
        "stats": {
            "num_tokens": len(tokens),
            "num_content_tokens": len(content_tokens),
            "num_unique_tokens": len({t.lower() for t in tokens}),
            "num_sentences": len(sentences),
        },
        "tokens_sample": tokens[:30],
        "lemmas_sample": lemmas[:30],
        "entities": extract_entities(text),
        "keywords": extract_keywords(text, top_keywords),
        "sentiment": analyze_sentiment(text),
        "engines": active_engines(),
    }
