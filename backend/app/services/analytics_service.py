"""
Analytics service — aggregates dashboard statistics.

Most figures are computed with database-side aggregation (GROUP BY / COUNT) for
efficiency rather than pulling rows into Python. Sentiment is the exception: it
isn't persisted, so it's computed on the fly over a capped slice of each
document's text — fine for a dashboard, and avoids a migration just to store it.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.models import ChatMessage, Document, User
from app.nlp import pipeline

logger = get_logger(__name__)

# Cap text scanned per document for sentiment, so the dashboard stays fast.
_SENTIMENT_SCAN_CHARS = 3000


def user_analytics(db: Session, user_id: int) -> dict[str, Any]:
    """Compute the analytics payload for a single user."""
    docs = list(
        db.execute(select(Document).where(Document.user_id == user_id)).scalars().all()
    )

    total_chars = sum(d.num_chars for d in docs)
    total_chunks = sum(d.num_chunks for d in docs)

    # Distributions (computed in Python here since we already hold the rows).
    file_types = Counter(d.file_ext or "unknown" for d in docs)
    categories = Counter(d.category or "Unclassified" for d in docs)

    # Uploads grouped by calendar date.
    uploads_by_date: Counter = Counter()
    for d in docs:
        uploads_by_date[d.created_at.date().isoformat()] += 1

    # Sentiment distribution — computed on the fly (not persisted).
    sentiment = Counter()
    for d in docs:
        if d.extracted_text.strip():
            label = pipeline.analyze_sentiment(d.extracted_text[:_SENTIMENT_SCAN_CHARS])["label"]
            sentiment[label] += 1

    # Search history = the user's chat questions (most recent first).
    searches = list(
        db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id, ChatMessage.role == "user")
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        ).scalars().all()
    )

    recent_docs = sorted(docs, key=lambda d: d.created_at, reverse=True)[:5]

    return {
        "total_documents": len(docs),
        "total_chars": total_chars,
        "total_chunks": total_chunks,
        "total_searches": db.scalar(
            select(func.count(ChatMessage.id)).where(
                ChatMessage.user_id == user_id, ChatMessage.role == "user"
            )
        ) or 0,
        "uploads_by_date": [
            {"date": k, "count": v} for k, v in sorted(uploads_by_date.items())
        ],
        "file_type_distribution": dict(file_types),
        "category_distribution": dict(categories),
        "sentiment_distribution": dict(sentiment),
        "recent_uploads": [
            {"id": d.id, "filename": d.filename, "file_ext": d.file_ext, "created_at": d.created_at}
            for d in recent_docs
        ],
        "recent_searches": [
            {"document_id": m.document_id, "question": m.content, "created_at": m.created_at}
            for m in searches
        ],
    }


def admin_analytics(db: Session) -> dict[str, Any]:
    """Compute platform-wide analytics for an admin."""
    total_users = db.scalar(select(func.count(User.id))) or 0
    total_documents = db.scalar(select(func.count(Document.id))) or 0
    total_searches = db.scalar(
        select(func.count(ChatMessage.id)).where(ChatMessage.role == "user")
    ) or 0

    # Documents per user (top 10), via a join + GROUP BY on the DB.
    rows = db.execute(
        select(User.username, func.count(Document.id))
        .join(Document, Document.user_id == User.id, isouter=True)
        .group_by(User.id)
        .order_by(func.count(Document.id).desc())
        .limit(10)
    ).all()

    # Platform-wide distributions.
    cat_rows = db.execute(
        select(Document.category, func.count(Document.id)).group_by(Document.category)
    ).all()
    ext_rows = db.execute(
        select(Document.file_ext, func.count(Document.id)).group_by(Document.file_ext)
    ).all()

    return {
        "total_users": total_users,
        "total_documents": total_documents,
        "total_searches": total_searches,
        "documents_per_user": [
            {"username": name, "document_count": count} for name, count in rows
        ],
        "category_distribution": {(c or "Unclassified"): n for c, n in cat_rows},
        "file_type_distribution": {(e or "unknown"): n for e, n in ext_rows},
    }
