"""
Document routes: upload, list (history), detail, and delete.

All endpoints require authentication, and a user can only ever see, retrieve, or
delete documents under their own account. Domain errors from the service layer
are translated into precise HTTP status codes, and every response shape is
declared for accurate OpenAPI / Swagger documentation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.db.models import User
from app.db.session import get_db
from app.schemas.document import DocumentDetail, DocumentRead
from app.services import document_service
from app.services.document_service import (
    DocumentNotFoundError,
    TextExtractionError,
    UnsupportedFileTypeError,
)

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    responses={
        400: {"description": "Empty file"},
        413: {"description": "File exceeds the size limit"},
        415: {"description": "Unsupported file type (only PDF, DOCX, TXT)"},
        422: {"description": "Text extraction failed"},
    },
)
async def upload_document(
    file: UploadFile = File(..., description="A PDF, DOCX, or TXT file."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    """
    Upload a **PDF**, **DOCX**, or **TXT** file.

    The server extracts the text, cleans it, stores the source file on disk, and
    persists a document record owned by the authenticated user.
    """
    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty."
        )
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.MAX_UPLOAD_MB} MB upload limit.",
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


@router.get(
    "",
    response_model=list[DocumentRead],
    summary="List documents (upload history)",
)
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentRead]:
    """Return all documents owned by the authenticated user, newest first."""
    documents = document_service.list_documents_for_user(db, current_user.id)
    return [DocumentRead.model_validate(d) for d in documents]


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Get a document with its cleaned text",
    responses={404: {"description": "Document not found"}},
)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentDetail:
    """Return a single document (metadata + cleaned text) the user owns."""
    try:
        document = document_service.get_document(db, current_user.id, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return DocumentDetail.model_validate(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    responses={404: {"description": "Document not found"}},
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Delete a document (DB row + stored file). Returns 204 on success."""
    try:
        document_service.delete_document(db, current_user.id, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    # Explicit empty Response — a 204 must not carry a body, and returning a
    # Response (rather than `-> None`) avoids FastAPI's response-model inference.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
