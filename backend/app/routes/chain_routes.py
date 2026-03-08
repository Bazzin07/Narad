"""
Topic Routes — topic distribution and articles by topic.
Chains feature has been removed in favor of on-demand event intelligence.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Topics"])



@router.get("/topics")
async def get_topic_distribution(
    db: AsyncSession = Depends(get_db),
):
    """Get a breakdown of articles by topic classification."""
    from sqlalchemy import func, select
    from app.models.article import Article

    result = await db.execute(
        select(Article.topic, func.count(Article.id))
        .group_by(Article.topic)
        .order_by(func.count(Article.id).desc())
    )
    rows = result.all()

    return {
        "topics": [{"topic": topic or "general", "count": count} for topic, count in rows],
        "total_articles": sum(count for _, count in rows),
    }


@router.get("/topics/{topic}")
async def get_articles_by_topic(
    topic: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get articles filtered by topic classification."""
    from sqlalchemy import select
    from app.models.article import Article

    result = await db.execute(
        select(Article)
        .where(Article.topic == topic)
        .order_by(Article.published_at.desc())
        .limit(limit)
    )
    articles = result.scalars().all()

    return {
        "topic": topic,
        "count": len(articles),
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "source": a.source,
                "language": a.language,
                "published_at": str(a.published_at),
                "topic": a.topic,
            }
            for a in articles
        ],
    }
