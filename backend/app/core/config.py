"""
Centralised application configuration.

All runtime settings are loaded from environment variables (or a local `.env`
file) via pydantic-settings. This gives us a single, type-validated source of
truth for configuration — no scattered `os.getenv` calls, no untyped strings.

Usage:
    from app.core.config import get_settings
    settings = get_settings()
    print(settings.DATABASE_URL)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = three levels up from this file
# (backend/app/core/config.py -> backend/app/core -> backend/app -> backend -> ROOT).
# Anchoring paths here makes the app independent of the current working
# directory, so it behaves identically whether launched from the repo root,
# the `backend/` folder, or inside a Docker container.
BASE_DIR: Path = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Strongly-typed application settings sourced from the environment."""

    # --- Application -------------------------------------------------------
    APP_NAME: str = "AI Document Intelligence Platform"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True

    # --- API server --------------------------------------------------------
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:8501", "http://127.0.0.1:8501"]
    )

    # --- Database ----------------------------------------------------------
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # --- Authentication / JWT ----------------------------------------------
    # SECURITY: override JWT_SECRET_KEY in .env for any non-local deployment.
    JWT_SECRET_KEY: str = "CHANGE_ME_dev_only_insecure_secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Generative AI -----------------------------------------------------
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # --- ML / NLP ----------------------------------------------------------
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    SPACY_MODEL: str = "en_core_web_sm"
    FAISS_INDEX_PATH: str = "./data/faiss_index"
    CHURN_MODEL_PATH: str = "./backend/app/ml/artifacts/churn_model.joblib"

    # Pydantic config: read from `.env`, ignore unknown keys, case-insensitive.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        """Allow CORS_ORIGINS to be provided as a comma-separated string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def gemini_enabled(self) -> bool:
        """True only when a non-placeholder Gemini key is configured."""
        key = self.GEMINI_API_KEY.strip()
        return bool(key) and key != "your_gemini_api_key_here"

    @property
    def sqlite_path(self) -> Path | None:
        """
        Absolute filesystem path to the SQLite DB file, or None for non-SQLite
        backends (e.g. PostgreSQL). Relative paths are anchored to BASE_DIR so
        the database location never depends on the process's working directory.
        """
        url = self.DATABASE_URL
        if not url.startswith("sqlite"):
            return None
        # Strip the "sqlite:///" (3 slashes) or "sqlite:////" (absolute) prefix.
        raw = url.split("sqlite:///", 1)[-1]
        path = Path(raw)
        return path if path.is_absolute() else (BASE_DIR / path).resolve()

    @property
    def database_url(self) -> str:
        """
        The connection URL the engine should actually use. For SQLite we return
        an absolute path so it resolves consistently from any CWD.
        """
        if self.sqlite_path is not None:
            return f"sqlite:///{self.sqlite_path.as_posix()}"
        return self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    `lru_cache` ensures the `.env` file is parsed only once per process, so
    every module shares the same immutable settings object.
    """
    return Settings()
