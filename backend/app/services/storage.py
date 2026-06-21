"""
File storage service.

Persists raw uploaded files to the local filesystem under a per-user directory.
Abstracting storage behind these functions means we can later swap the local
disk for S3/Azure Blob by changing only this module — callers stay unchanged.

Files are saved as `<UPLOAD_DIR>/<user_id>/<uuid>__<safe_filename>` so:
  * uploads are namespaced per user (no cross-user collisions),
  * a random UUID prevents two same-named files from overwriting each other,
  * the original name is preserved (after sanitisation) for readability.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Allow only safe filename characters; everything else becomes "_".
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(filename: str) -> str:
    """Strip path components and unsafe characters to prevent path traversal."""
    # `Path(...).name` defeats "../" and absolute-path injection attempts.
    base = Path(filename).name
    safe = _UNSAFE.sub("_", base).strip("._") or "file"
    return safe[:200]  # cap length for filesystem safety


def save_file(user_id: int, filename: str, data: bytes) -> Path:
    """
    Persist raw bytes for a user and return the absolute storage path.

    Creates the per-user directory on demand.
    """
    user_dir = get_settings().upload_path / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(filename)
    target = user_dir / f"{uuid.uuid4().hex}__{safe_name}"

    target.write_bytes(data)
    logger.info("Saved file | user=%s | path=%s | bytes=%s", user_id, target, len(data))
    return target


def delete_file(storage_path: str) -> bool:
    """
    Delete a stored file. Returns True if removed, False if it was already
    absent. Never raises on a missing file (idempotent cleanup).
    """
    if not storage_path:
        return False
    path = Path(storage_path)
    try:
        if path.exists():
            path.unlink()
            logger.info("Deleted file | path=%s", path)
            return True
        logger.warning("File already absent on delete | path=%s", path)
        return False
    except OSError:
        logger.exception("Failed to delete file | path=%s", path)
        return False
