"""
Application-wide logging configuration.

We configure logging once, at startup, so every module can simply call
`logging.getLogger(__name__)` and get consistent, structured output to both the
console and a rotating log file. Centralising this avoids each module inventing
its own ad-hoc print statements.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

from app.core.config import get_settings

# Directory where rotating log files are written.
_LOG_DIR = Path("logs")
_LOG_FILE = _LOG_DIR / "app.log"

# Module-level guard so repeated calls don't add duplicate handlers.
_CONFIGURED = False

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    """
    Initialise root logging handlers (console + rotating file).

    Idempotent: safe to call multiple times (e.g. from both API and frontend).
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_LOG_FORMAT)

    # Console handler — human-readable output during development.
    console = logging.StreamHandler()
    console.setFormatter(formatter)

    # Rotating file handler — keeps 5 files of 2 MB each so logs never grow
    # unbounded on disk (important for long-running production processes).
    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    # Clear any pre-existing handlers (e.g. uvicorn's default) to avoid dupes.
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)

    # Tame noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

    _CONFIGURED = True
    logging.getLogger(__name__).info(
        "Logging configured | level=%s | env=%s", settings.LOG_LEVEL, settings.ENVIRONMENT
    )


def get_logger(name: str) -> logging.Logger:
    """Convenience accessor that guarantees logging is configured first."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)
