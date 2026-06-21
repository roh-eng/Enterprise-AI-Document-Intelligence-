"""
Text preprocessing for the classification model.

Preprocessing turns raw document text into a normalised bag of tokens that
TF-IDF can vectorise. The transformation is deterministic and dependency-free
(pure regex + a built-in stopword list) so it runs identically at train time and
inference time — a mismatch between the two is a classic source of "great in
training, terrible in production" bugs.

This single `preprocess` function is passed to scikit-learn's TfidfVectorizer,
guaranteeing the exact same cleaning is baked into the persisted pipeline.
"""

from __future__ import annotations

import re

# A compact English stopword list. Stopwords ("the", "and", "of") appear in
# every document, carry no class signal, and only add noise/dimensionality.
STOPWORDS: frozenset[str] = frozenset(
    """
    a an the and or but if then else for to of in on at by with without within
    is are was were be been being am do does did doing have has had having
    this that these those i you he she it we they them his her its our your their
    as from into over under again further once here there all any both each few
    more most other some such no nor not only own same so than too very can will
    just should now also which who whom what when where why how about against
    between during before after above below up down out off out per via
    """.split()
)

# Match alphabetic word tokens of length >= 2 (drops numbers & single letters).
_TOKEN_RE = re.compile(r"[a-z]{2,}")


def preprocess(text: str) -> str:
    """
    Lowercase, tokenise to alphabetic words, and drop stopwords.

    Returns a single space-joined string of clean tokens (the form
    TfidfVectorizer expects). Returns "" for empty input — never raises.
    """
    if not text:
        return ""
    tokens = _TOKEN_RE.findall(text.lower())
    kept = [tok for tok in tokens if tok not in STOPWORDS]
    return " ".join(kept)
