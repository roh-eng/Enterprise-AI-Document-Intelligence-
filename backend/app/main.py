"""
FastAPI application entrypoint.

This module wires the application together:
  * configures logging,
  * creates the FastAPI app with OpenAPI metadata,
  * registers CORS middleware (so the Streamlit frontend can call the API),
  * initialises the database on startup,
  * exposes a `/health` endpoint for liveness checks.

Feature routers (documents, analytics, RAG) are mounted in later steps.

Run with:  uvicorn app.main:app --reload   (from the `backend/` directory)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging_config import configure_logging, get_logger
from app.db.session import init_db

configure_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks (modern replacement for on_event)."""
    logger.info("Starting %s | env=%s", settings.APP_NAME, settings.ENVIRONMENT)
    init_db()
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Production-grade AI Document Intelligence Platform combining classical "
        "ML, NLP, deep-learning embeddings, and Generative AI (RAG)."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the Streamlit dev server to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health_check() -> dict:
    """Liveness probe. Returns service status and key feature availability."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "gemini_enabled": settings.gemini_enabled,
    }


@app.get("/", tags=["system"])
def root() -> dict:
    """Friendly root pointing to the interactive API docs."""
    return {"message": f"{settings.APP_NAME} API. See /docs for documentation."}
