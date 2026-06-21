"""
Generative AI routes: run a generation task (summary, FAQ, interview questions,
explanation, action items, deadlines) on text or a stored document.

A single flexible endpoint keeps the API surface small while supporting six
tasks against two input sources.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.db.models import User
from app.db.session import get_db
from app.genai import gemini_client
from app.schemas.genai import GenAIStatus, GenerateRequest, GenerateResponse
from app.services import genai_service
from app.services.document_service import DocumentNotFoundError

logger = get_logger(__name__)

router = APIRouter(prefix="/genai", tags=["generative-ai"])


@router.get("/status", response_model=GenAIStatus, summary="GenAI availability")
def status_check(_user: User = Depends(get_current_user)) -> GenAIStatus:
    """Report whether live Gemini generation is configured (else fallback runs)."""
    settings = get_settings()
    return GenAIStatus(gemini_enabled=gemini_client.is_available(), model=settings.GEMINI_MODEL)


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Run a generation task on text or a document",
    responses={
        404: {"description": "Document not found"},
        422: {"description": "Invalid input (need exactly one of text/document_id)"},
    },
)
def generate(
    payload: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateResponse:
    """
    Generate content for one of: summary, explain, faq, interview_questions,
    action_items, deadlines. Provide either `text` or `document_id`.
    """
    try:
        result = genai_service.generate(
            db,
            user_id=current_user.id,
            task=payload.task.value,
            text=payload.text,
            document_id=payload.document_id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        logger.exception("Unexpected error during generation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Generation failed"
        )

    return GenerateResponse(**result)
