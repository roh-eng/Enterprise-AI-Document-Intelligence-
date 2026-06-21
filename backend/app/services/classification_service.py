"""
Classification service — bridges the ML model and the document domain.

Keeps the API layer free of ML details: routes call these functions, which use
the inference classifier and persist results back onto the Document row.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.ml import classifier
from app.ml.classifier import Prediction
from app.services import document_service

logger = get_logger(__name__)

# Re-export so routes can catch a single, domain-level error type.
ModelNotTrainedError = classifier.ModelNotTrainedError


def classify_text(text: str) -> Prediction:
    """Classify arbitrary text (no persistence)."""
    return classifier.classify(text)


def classify_document(db: Session, user_id: int, document_id: int) -> Prediction:
    """
    Classify a stored document and persist the predicted category + confidence.

    Ownership is enforced via `document_service.get_document` (raises
    DocumentNotFoundError for documents the user doesn't own).
    """
    document = document_service.get_document(db, user_id, document_id)
    prediction = classifier.classify(document.extracted_text)

    document.category = prediction.category
    document.category_confidence = prediction.confidence
    db.commit()
    db.refresh(document)
    logger.info(
        "Classified document | id=%s | user=%s | category=%s | conf=%.3f",
        document_id, user_id, prediction.category, prediction.confidence,
    )
    return prediction
