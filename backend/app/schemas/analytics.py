"""
Pydantic schemas for the analytics dashboard.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DateCount(BaseModel):
    """A (date, count) point for time-series charts."""

    date: str
    count: int


class RecentUpload(BaseModel):
    id: int
    filename: str
    file_ext: str
    created_at: datetime


class RecentSearch(BaseModel):
    """A past chat question (the user's search history)."""

    document_id: int
    question: str
    created_at: datetime


class UserAnalytics(BaseModel):
    """Per-user dashboard analytics."""

    total_documents: int
    total_chars: int
    total_chunks: int
    total_searches: int
    uploads_by_date: list[DateCount]
    file_type_distribution: dict[str, int]
    category_distribution: dict[str, int]
    sentiment_distribution: dict[str, int]
    recent_uploads: list[RecentUpload]
    recent_searches: list[RecentSearch]


class UserStat(BaseModel):
    username: str
    document_count: int


class AdminAnalytics(BaseModel):
    """Platform-wide analytics (admin only)."""

    total_users: int
    total_documents: int
    total_searches: int
    documents_per_user: list[UserStat]
    category_distribution: dict[str, int]
    file_type_distribution: dict[str, int]
