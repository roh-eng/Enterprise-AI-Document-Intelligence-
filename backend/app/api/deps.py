"""
Reusable FastAPI dependencies for the API layer.

`get_current_user` is the gatekeeper for protected endpoints: it extracts the
bearer token, validates it, loads the user, and raises 401 otherwise. Endpoints
opt into authentication simply by declaring it as a parameter:

    def endpoint(user: User = Depends(get_current_user)): ...
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db
from app.services import user_service

logger = get_logger(__name__)

# Tells Swagger UI where to obtain a token and enables the "Authorize" button.
# tokenUrl is relative to the app root and must match the login route path.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Standard 401 raised whenever authentication fails.
_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the authenticated user from a JWT bearer token.

    Raises 401 if the token is missing/invalid/expired or the user no longer
    exists; 403 if the account has been deactivated.
    """
    claims = decode_access_token(token)
    if claims is None:
        raise _credentials_exception

    subject = claims.get("sub")
    if subject is None:
        raise _credentials_exception

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise _credentials_exception

    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise _credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account"
        )
    return user
