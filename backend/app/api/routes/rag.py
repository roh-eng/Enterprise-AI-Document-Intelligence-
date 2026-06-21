"""
RAG routes: index a document, chat with it, and manage conversation history.

All endpoints are document-scoped and require authentication; ownership is
enforced in the service layer.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging_config import get_logger
from app.db.models import User
from app.db.session import get_db
from app.schemas.rag import ChatMessageOut, ChatRequest, ChatResponse, IndexResponse
from app.services import rag_service
from app.services.document_service import DocumentNotFoundError

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["rag-chat"])


@router.post(
    "/{document_id}/index",
    response_model=IndexResponse,
    summary="Chunk & index a document into the vector store",
    responses={404: {"description": "Document not found"}},
)
def index_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IndexResponse:
    """Split the document into chunks, embed them, and build its FAISS index."""
    try:
        result = rag_service.index_document(db, current_user.id, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return IndexResponse(**result)


@router.post(
    "/{document_id}/chat",
    response_model=ChatResponse,
    summary="Ask a question about a document (RAG)",
    responses={404: {"description": "Document not found"}},
)
def chat(
    document_id: int,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Retrieve relevant chunks and answer the question with source citations."""
    try:
        result = rag_service.chat(db, current_user.id, document_id, payload.question)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ChatResponse(**result)


@router.get(
    "/{document_id}/chat/history",
    response_model=list[ChatMessageOut],
    summary="Get conversation history",
    responses={404: {"description": "Document not found"}},
)
def chat_history(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatMessageOut]:
    """Return the full conversation history for a document."""
    try:
        messages = rag_service.history(db, current_user.id, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return [ChatMessageOut(**m) for m in messages]


@router.delete(
    "/{document_id}/chat/history",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear conversation history",
    responses={404: {"description": "Document not found"}},
)
def clear_chat_history(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Delete a document's conversation history."""
    try:
        rag_service.clear_history(db, current_user.id, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
