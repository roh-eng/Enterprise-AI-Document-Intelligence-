"""
Pydantic schemas for ML classification responses.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    """The predicted category for a piece of text, with confidence."""

    category: str = Field(examples=["Invoice"])
    confidence: float = Field(ge=0.0, le=1.0, examples=[0.94])
    probabilities: dict[str, float] = Field(
        description="Probability for every category (sums to ~1.0)."
    )
    model_name: str = Field(examples=["XGBoost"])


class TextIn(BaseModel):
    """Free-text input for ad-hoc classification."""

    text: str = Field(min_length=1, examples=["Invoice number 4471 total amount due..."])


class ModelInfo(BaseModel):
    """Metadata about the deployed classification model."""

    model_name: str
    categories: list[str]
    trained_at: str
