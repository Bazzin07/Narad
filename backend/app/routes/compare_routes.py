"""
Impact Analysis & Cluster Routes.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import CompareRequest, CompareResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Impact Analysis & Clusters"])


@router.post("/compare", response_model=CompareResponse)
async def compare_events(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Feature 2: Impact Analysis — explain how two events affect each other.
    Works across different domains (e.g., war → oil prices, policy → markets).
    """
    from app.main import orchestrator

    try:
        result = await orchestrator.compare_events(
            article1_id=request.article1_id,
            article2_id=request.article2_id,
            session_id=request.session_id,
            db=db,
            preferred_language=request.preferred_language,
            detailed=request.detailed,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Impact analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/clusters")
async def list_clusters(
    db: AsyncSession = Depends(get_db),
):
    """Get all event clusters with member counts."""
    from app.main import orchestrator
    clusters = await orchestrator.clustering.get_all_clusters(db)
    return {"clusters": clusters, "total": len(clusters)}


@router.get("/clusters/{cluster_id}")
async def get_cluster(
    cluster_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get details for a specific cluster, including member articles."""
    from app.main import orchestrator
    members = await orchestrator.clustering.get_cluster_members(cluster_id, db)
    if not members:
        raise HTTPException(status_code=404, detail="Cluster not found")

    articles = []
    for aid in members:
        detail = await orchestrator.get_article_detail(aid, db)
        if detail:
            articles.append(detail)

    return {
        "cluster_id": cluster_id,
        "member_count": len(articles),
        "articles": articles,
    }
