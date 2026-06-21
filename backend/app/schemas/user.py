"""
Pydantic schemas for users and authentication.

Schemas are the API's *contract*: they validate incoming JSON and shape
outgoing JSON. Crucially, the response schema (`UserRead`) has NO password
field, so a hash can never accidentally leak to a client.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Fields common to creating and reading a user."""

    username: str = Field(min_length=3, max_length=50, examples=["jane_doe"])
    email: EmailStr = Field(examples=["jane@example.com"])


class UserCreate(UserBase):
    """Registration payload (input only)."""

    password: str = Field(min_length=8, max_length=128, examples=["S3curePass!"])


class UserRead(UserBase):
    """Public user representation returned by the API (never includes secrets)."""

    id: int
    is_active: bool
    created_at: datetime

    # Allow building this schema directly from a SQLAlchemy ORM object.
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """OAuth2-style token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded JWT claims we care about internally."""

    user_id: int | None = None
    username: str | None = None
