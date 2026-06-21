"""
Document routes: upload and list. All endpoints require authentication, and a
user can only ever see or create documents under their own account.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging_config import get_logger
from app.db.models import User
from app.db.session import get_db
from app.schemas.document import DocumentRead
from app.services import document_service
from app.services.document_service import (
    TextExtractionError,
    UnsupportedFileTypeError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# 10 MB upload ceiling — protects the server from oversized payloads.
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    """
    Upload a PDF or TXT file, extract its text, and store it for the user.

    Returns the stored document's metadata. Responds 413 if too large, 415 for
    unsupported types, and 422 if text extraction fails.
    """
    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 10 MB upload limit.",
        )
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty."
        )

    try:
        document = document_service.create_document(
            db,
            user_id=current_user.id,
            filename=file.filename or "untitled",
            content_type=file.content_type or "application/octet-stream",
            raw=raw,
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        )
    except TextExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    except Exception:
        logger.exception("Unexpected error during document upload")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload failed",
        )

    return DocumentRead.model_validate(document)


@router.get("", response_model=list[DocumentRead])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentRead]:
    """List all documents owned by the authenticated user (newest first)."""
    documents = document_service.list_documents_for_user(db, current_user.id)
    return [DocumentRead.model_validate(d) for d in documents]
