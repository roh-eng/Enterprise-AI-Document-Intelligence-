"""
Inference-time document classifier.

Loads the persisted pipeline (TF-IDF + best model + label encoder) once and
serves predictions. Lazy, cached loading means the (relatively expensive) joblib
load happens on first use, not at import, and the model stays warm in memory
across requests.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import joblib

from app.core.logging_config import get_logger
from app.ml.train import MODEL_PATH

logger = get_logger(__name__)


class ModelNotTrainedError(Exception):
    """Raised when no saved model artifact exists yet."""


@dataclass
class Prediction:
    """Result of classifying a single document."""

    category: str
    confidence: float
    probabilities: dict[str, float]
    model_name: str


@lru_cache(maxsize=1)
def _load_bundle() -> dict[str, Any]:
    """Load and cache the saved model bundle (pipeline + encoder + metadata)."""
    if not MODEL_PATH.exists():
        raise ModelNotTrainedError(
            "No trained model found. Run `python -m app.ml.train` first."
        )
    logger.info("Loading classifier model from %s", MODEL_PATH)
    return joblib.load(MODEL_PATH)


def model_info() -> dict[str, Any]:
    """Return metadata about the loaded model (name, categories, train time)."""
    bundle = _load_bundle()
    return {
        "model_name": bundle["model_name"],
        "categories": bundle["categories"],
        "trained_at": bundle["trained_at"],
    }


def classify(text: str) -> Prediction:
    """
    Classify a document's text into one of the trained categories.

    Returns a Prediction with the winning category, its confidence (the model's
    probability for that class), and the full probability distribution. Raises
    ModelNotTrainedError if no model has been trained, ValueError for empty text.
    """
    if not text or not text.strip():
        raise ValueError("Cannot classify empty text.")

    bundle = _load_bundle()
    pipeline = bundle["pipeline"]
    encoder = bundle["label_encoder"]

    # predict_proba gives a probability per class; argmax is the prediction.
    proba = pipeline.predict_proba([text])[0]
    classes = encoder.inverse_transform(range(len(proba)))
    probabilities = {str(cls): float(p) for cls, p in zip(classes, proba)}

    best_idx = int(proba.argmax())
    category = str(classes[best_idx])
    confidence = float(proba[best_idx])

    return Prediction(
        category=category,
        confidence=confidence,
        probabilities=probabilities,
        model_name=bundle["model_name"],
    )
