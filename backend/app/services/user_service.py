"""
User service — business logic for accounts and authentication.

The service layer sits between the API (HTTP) and the database (ORM). It owns
the rules ("usernames must be unique", "passwords are hashed before storage")
so those rules are reusable and testable without spinning up a web server.

Routes call these functions; they never touch password hashing or the ORM
directly.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.security import hash_password, verify_password
from app.db.models import User
from app.schemas.user import UserCreate

logger = get_logger(__name__)


class DuplicateUserError(Exception):
    """Raised when a username or email is already registered."""


def get_user_by_username(db: Session, username: str) -> User | None:
    """Look up a user by username (returns None if not found)."""
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Look up a user by email (returns None if not found)."""
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Look up a user by primary key."""
    return db.get(User, user_id)


def create_user(db: Session, payload: UserCreate) -> User:
    """
    Register a new user.

    Hashes the password, enforces uniqueness of username/email, and persists the
    row. Raises `DuplicateUserError` if either identifier is taken.
    """
    if get_user_by_username(db, payload.username):
        raise DuplicateUserError("Username already registered")
    if get_user_by_email(db, payload.email):
        raise DuplicateUserError("Email already registered")

    # Bootstrap: the very first registered user becomes the admin. This avoids
    # shipping hard-coded credentials while still giving the platform an owner.
    is_first_user = db.query(User.id).first() is None

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_admin=is_first_user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # populate auto-generated fields (id, created_at)
    logger.info("Registered new user | id=%s | username=%s", user.id, user.username)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """
    Validate credentials.

    Returns the user on success, or None if the username is unknown, the
    password is wrong, or the account is disabled. We deliberately return the
    same None for "no such user" and "bad password" to avoid leaking which
    usernames exist (user-enumeration defence).
    """
    user = get_user_by_username(db, username)
    if user is None:
        logger.info("Login failed | unknown username=%s", username)
        return None
    if not verify_password(password, user.hashed_password):
        logger.info("Login failed | bad password | username=%s", username)
        return None
    if not user.is_active:
        logger.info("Login blocked | inactive account | username=%s", username)
        return None
    return user
