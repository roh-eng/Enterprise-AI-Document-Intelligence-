"""
ML routes: ad-hoc text classification and model introspection.

These endpoints require authentication. Document-bound classification lives on
the /documents router; here we expose stateless text classification and a
model-info endpoint for the UI to display which model is deployed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.logging_config import get_logger
from app.db.models import User
from app.schemas.classification import ClassificationResult, ModelInfo, TextIn
from app.services import classification_service
from app.services.classification_service import ModelNotTrainedError

logger = get_logger(__name__)

router = APIRouter(prefix="/ml", tags=["machine-learning"])


@router.post(
    "/classify",
    response_model=ClassificationResult,
    summary="Classify arbitrary text",
    responses={503: {"description": "Model not trained yet"}},
)
def classify_text(
    payload: TextIn,
    _user: User = Depends(get_current_user),
) -> ClassificationResult:
    """Classify free text into one of: Resume, Invoice, Legal, Medical, Research."""
    try:
        pred = classification_service.classify_text(payload.text)
    except ModelNotTrainedError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return ClassificationResult(
        category=pred.category,
        confidence=pred.confidence,
        probabilities=pred.probabilities,
        model_name=pred.model_name,
    )


@router.get(
    "/model-info",
    response_model=ModelInfo,
    summary="Deployed model metadata",
    responses={503: {"description": "Model not trained yet"}},
)
def get_model_info(_user: User = Depends(get_current_user)) -> ModelInfo:
    """Return which model is deployed, its categories, and when it was trained."""
    from app.ml import classifier

    try:
        info = classifier.model_info()
    except ModelNotTrainedError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return ModelInfo(**info)
