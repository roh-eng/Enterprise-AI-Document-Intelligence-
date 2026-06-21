"""
Analytics routes: per-user dashboard stats and (admin-only) platform stats.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_user
from app.core.logging_config import get_logger
from app.db.models import User
from app.db.session import get_db
from app.schemas.analytics import AdminAnalytics, UserAnalytics
from app.services import analytics_service

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/me", response_model=UserAnalytics, summary="Current user's analytics")
def my_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserAnalytics:
    """Upload, classification, sentiment, and search statistics for the user."""
    return UserAnalytics(**analytics_service.user_analytics(db, current_user.id))


@router.get(
    "/admin",
    response_model=AdminAnalytics,
    summary="Platform-wide analytics (admin only)",
    responses={403: {"description": "Admin access required"}},
)
def admin_dashboard(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> AdminAnalytics:
    """Aggregate statistics across all users and documents."""
    return AdminAnalytics(**analytics_service.admin_analytics(db))
