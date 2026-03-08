"""
Source Health Routes — monitor source status, re-enable disabled sources.
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Source Health"])


@router.get("/sources/health")
async def get_source_health(db: AsyncSession = Depends(get_db)):
    """
    Get health status for all RSS sources.
    Returns: list of sources with status (healthy|degraded|failing|disabled|stale|unknown),
    failure counts, fetch counts, and recent article counts.
    """
    from app.main import ingestion_service
    health = await ingestion_service.get_source_health(db)

    # Summary stats
    statuses = [s["status"] for s in health]
    summary = {
        "total_sources": len(health),
        "healthy": statuses.count("healthy"),
        "degraded": statuses.count("degraded"),
        "failing": statuses.count("failing"),
        "disabled": statuses.count("disabled"),
        "stale": statuses.count("stale"),
        "unknown": statuses.count("unknown"),
    }

    return {"summary": summary, "sources": health}


@router.post("/sources/{source_id}/enable")
async def enable_source(source_id: str, db: AsyncSession = Depends(get_db)):
    """Re-enable a disabled source and reset its failure count."""
    from sqlalchemy import select
    from app.models.article import Source

    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Source not found")

    source.active = True
    source.consecutive_failures = 0
    await db.commit()
    return {"message": f"Source '{source.name}' re-enabled", "source_id": source_id}


@router.post("/sources/{source_id}/disable")
async def disable_source(source_id: str, db: AsyncSession = Depends(get_db)):
    """Manually disable a source."""
    from sqlalchemy import select
    from app.models.article import Source

    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Source not found")

    source.active = False
    await db.commit()
    return {"message": f"Source '{source.name}' disabled", "source_id": source_id}
