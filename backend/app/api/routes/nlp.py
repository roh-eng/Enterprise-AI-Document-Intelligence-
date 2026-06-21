"""
NLP routes: text analysis and text-to-text similarity.

Document-scoped NLP (analyse a stored doc, find similar docs) lives on the
/documents router; here we expose the stateless, text-based operations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.logging_config import get_logger
from app.db.models import User
from app.nlp import embeddings
from app.schemas.nlp import NLPAnalysis, SimilarityScore, TextIn, TwoTextsIn
from app.services import nlp_service

logger = get_logger(__name__)

router = APIRouter(prefix="/nlp", tags=["nlp"])


@router.post("/analyze", response_model=NLPAnalysis, summary="Full NLP analysis of text")
def analyze(payload: TextIn, _user: User = Depends(get_current_user)) -> NLPAnalysis:
    """
    Tokenise, remove stopwords, lemmatise, extract entities & keywords, and score
    sentiment for the supplied text.
    """
    try:
        result = nlp_service.analyze_text(payload.text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return NLPAnalysis(**result)


@router.post("/similarity", response_model=SimilarityScore, summary="Similarity of two texts")
def similarity(payload: TwoTextsIn, _user: User = Depends(get_current_user)) -> SimilarityScore:
    """Compute the cosine similarity between two texts via sentence embeddings."""
    score = nlp_service.text_similarity(payload.text_a, payload.text_b)
    return SimilarityScore(similarity=score, backend=embeddings.embedding_backend())
