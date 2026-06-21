"""
Pydantic schemas for NLP endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TextIn(BaseModel):
    """Free-text input for NLP analysis."""

    text: str = Field(min_length=1)


class TwoTextsIn(BaseModel):
    """Two texts to compare for similarity."""

    text_a: str = Field(min_length=1)
    text_b: str = Field(min_length=1)


class EntityItem(BaseModel):
    text: str
    label: str


class KeywordItem(BaseModel):
    term: str
    score: float


class SentimentResult(BaseModel):
    label: str
    score: float
    engine: str


class NLPStats(BaseModel):
    num_tokens: int
    num_content_tokens: int
    num_unique_tokens: int
    num_sentences: int


class NLPAnalysis(BaseModel):
    """Full NLP analysis of a piece of text."""

    stats: NLPStats
    tokens_sample: list[str]
    lemmas_sample: list[str]
    entities: list[EntityItem]
    keywords: list[KeywordItem]
    sentiment: SentimentResult
    engines: dict[str, str]


class SimilarityScore(BaseModel):
    """Cosine similarity between two texts."""

    similarity: float = Field(ge=0.0, le=1.0)
    backend: str


class SimilarDocument(BaseModel):
    document_id: int
    filename: str
    similarity: float


class SimilarDocumentsResponse(BaseModel):
    target_id: int
    backend: str
    results: list[SimilarDocument]
