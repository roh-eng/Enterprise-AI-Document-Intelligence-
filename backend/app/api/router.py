"""
Top-level API router.

Aggregates every feature router into a single `api_router` that `main.py`
includes once. Adding a new feature = create its route module and include it
here — `main.py` never changes.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, documents, genai, ml, nlp

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(ml.router)
api_router.include_router(nlp.router)
api_router.include_router(genai.router)
