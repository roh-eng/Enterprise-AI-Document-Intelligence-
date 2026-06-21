"""
Authentication routes: registration, login (token issue), and current-user.

Route handlers stay thin: they validate input (via schemas), delegate to the
service layer, and translate domain errors into HTTP responses. No business
logic or SQL lives here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging_config import get_logger
from app.core.security import create_access_token
from app.db.models import User
from app.db.session import get_db
from app.schemas.user import Token, UserCreate, UserRead
from app.services import user_service
from app.services.user_service import DuplicateUserError

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """
    Register a new user account.

    Returns the created user (without any secret fields). Responds 409 if the
    username or email is already taken.
    """
    try:
        return user_service.create_user(db, payload)
    except DuplicateUserError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception:
        logger.exception("Unexpected error during registration")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """
    Exchange username + password for a JWT access token.

    Uses the OAuth2 password flow (form fields `username`/`password`) so the
    Swagger "Authorize" button works out of the box. Returns 401 on bad
    credentials.
    """
    user = user_service.authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=user.id, extra_claims={"username": user.username})
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the profile of the authenticated user (protected endpoint)."""
    return current_user
