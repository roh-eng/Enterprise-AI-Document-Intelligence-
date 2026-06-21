"""
Security primitives: password hashing and JWT access tokens.

This module is deliberately framework-agnostic — it knows nothing about HTTP or
SQLAlchemy. It exposes pure functions the service/API layers build on:

  * hash_password / verify_password  — bcrypt via passlib.
  * create_access_token / decode_access_token — signed JWTs via PyJWT.

Keeping all crypto in one audited place means there is exactly one code path to
review for security, and no module ever reimplements hashing ad-hoc.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt  # PyJWT
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# bcrypt is the industry standard for password storage: it is slow by design
# (work factor) and salts automatically, defeating rainbow-table attacks.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Return a salted bcrypt hash for a plaintext password."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check a plaintext password against a stored bcrypt hash.

    Returns False (never raises) on malformed hashes so callers can treat the
    result as a simple boolean auth decision.
    """
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception:
        logger.warning("Password verification failed due to a malformed hash")
        return False


# ---------------------------------------------------------------------------
# JSON Web Tokens
# ---------------------------------------------------------------------------
def create_access_token(
    subject: str | int,
    expires_minutes: int | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT.

    Parameters
    ----------
    subject : the user identity placed in the standard `sub` claim.
    expires_minutes : token lifetime; defaults to the configured value.
    extra_claims : optional additional claims (e.g. username) merged in.
    """
    expire_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Validate and decode a JWT.

    Returns the claims dict on success, or None if the token is expired,
    tampered with, or otherwise invalid. Never raises — the API layer turns a
    None result into a 401.
    """
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        logger.info("Rejected an expired JWT")
        return None
    except jwt.InvalidTokenError as exc:
        logger.warning("Rejected an invalid JWT: %s", exc)
        return None
