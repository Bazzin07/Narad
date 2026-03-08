"""
News API Routes — listing, detail, ingestion, and deep analysis.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import ArticleSummary, ArticleDetail, IngestResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news", tags=["News"])


@router.get("", response_model=list[ArticleSummary])
async def get_news(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    language: Optional[str] = Query(None, description="Filter by language (en, hi, fr, etc.)"),
    region: Optional[str] = Query(None, description="Filter by region (india, global)"),
    state: Optional[str] = Query(None, description="Filter by Indian state (delhi, maharashtra, etc.)"),
    db: AsyncSession = Depends(get_db),
):
    """Get recent news articles, optionally filtered by language, region, and state."""
    from app.main import orchestrator
    return await orchestrator.get_recent_news(db, limit=limit, offset=offset, language=language, region=region, state=state)


@router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full details for a single article."""
    from app.main import orchestrator
    detail = await orchestrator.get_article_detail(article_id, db)
    if not detail:
        raise HTTPException(status_code=404, detail="Article not found")
    return detail


from fastapi import BackgroundTasks

async def run_ingestion_background():
    """Run the ingestion pipeline in the background using a fresh database session."""
    from app.main import orchestrator
    from app.database import async_session
    
    try:
        async with async_session() as db:
            logger.info("Starting manual background ingestion...")
            result = await orchestrator.run_full_pipeline(db)
            ingestion = result.get("ingestion", {})
            stored = ingestion.get("articles_stored", 0)
            logger.info(f"Manual background ingestion completed: {stored} articles stored.")
    except Exception as e:
        logger.error(f"Manual background ingestion failed: {e}", exc_info=True)


@router.post("/ingest")
async def trigger_ingestion(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger news ingestion from all configured sources (runs in background)."""
    # Trigger the heavy pipeline in the background so App Runner doesn't timeout
    background_tasks.add_task(run_ingestion_background)
    
    return {
        "status": "accepted",
        "message": "Ingestion started in the background. It takes 1-2 minutes to complete.",
    }


@router.post("/reprocess")
async def reprocess_articles(
    db: AsyncSession = Depends(get_db),
):
    """Rebuild FAISS index and re-cluster all articles."""
    from app.main import orchestrator

    count = await orchestrator.embedding.rebuild_index(db)
    clusters = await orchestrator.clustering.cluster_articles(db)

    return {
        "status": "completed",
        "articles_reprocessed": count,
        "clusters_found": len(clusters),
        "faiss_vectors": orchestrator.embedding.index.ntotal,
    }


@router.post("/backfill-geo-scope")
async def backfill_geo_scope(
    db: AsyncSession = Depends(get_db),
):
    """Backfill geographic_scope for all existing articles."""
    from sqlalchemy import select
    from app.models.article import Article, Source as SourceModel
    from app.services.geo_scope_classifier import classify_geo_scope

    # Scan ALL articles — reclassify every one
    result = await db.execute(
        select(Article, SourceModel.source_region)
        .outerjoin(SourceModel, Article.source_id == SourceModel.id)
    )
    rows = result.fetchall()

    updated = 0
    scope_counts = {"india": 0, "global": 0, "mixed": 0}
    for article, source_region in rows:
        new_scope = classify_geo_scope(
            title=article.title,
            content=article.content[:2000],
            source_region=source_region,
            language=article.language,
        )
        scope_counts[new_scope] = scope_counts.get(new_scope, 0) + 1
        if article.geographic_scope != new_scope:
            article.geographic_scope = new_scope
            updated += 1

    await db.commit()
    logger.info(f"Backfill geo scope: {updated}/{len(rows)} articles updated — {scope_counts}")
    return {
        "status": "completed",
        "total_scanned": len(rows),
        "articles_updated": updated,
        "scope_distribution": scope_counts,
    }

@router.post("/{article_id}/analyze")
async def analyze_article(
    article_id: str,
    session_id: str = Query("default"),
    db: AsyncSession = Depends(get_db),
):
    """
    Feature 1: Deep Analysis — get detailed breakdown of a news event.
    Returns: what happened, why it matters, context, implications, key players.
    """
    from app.main import orchestrator

    try:
        result = await orchestrator.analyze_article(article_id, session_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/{article_id}/explore")
async def explore_connections(
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Event Intelligence — On-demand exploration of event connections.

    Retrieves a broad candidate set, evaluates multi-signal relationships,
    and generates a structured narrative explaining how events connect.

    Returns:
      - related_events: connected articles with metadata
      - narrative: structured explanation of the event network
      - confidence: assessment of connection strength
      - signals_summary: breakdown of detected patterns
    """
    import asyncio
    from app.main import event_intelligence_service
    from app.services.cache_service import cache_get, cache_set, TTL_ANALYSIS

    # Check cache first
    explore_key = f"explore:{article_id}"
    cached = cache_get(explore_key)
    if cached:
        return cached

    try:
        result = await asyncio.wait_for(
            event_intelligence_service.explore_connections(
                seed_article_id=article_id,
                db=db,
            ),
            timeout=15.0,
        )
        # Cache for 30 minutes
        cache_set(explore_key, result, TTL_ANALYSIS)
        return result
    except asyncio.TimeoutError:
        logger.warning(f"Explore timed out for {article_id}")
        raise HTTPException(status_code=504, detail="Analysis timed out. Try again later.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Explore failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Exploration failed: {str(e)}")


@router.get("/{article_id}/fact-sheet")
async def get_fact_sheet(
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Multi-Source Fact Sheet — aggregates coverage of the same event
    across all available sources and languages into a consolidated report.

    Returns:
      - coverage: sources count, languages, date range
      - key_entities: entities mentioned across sources
      - source_perspectives: how each source covers the event
      - timeline: chronological order of coverage
      - narrative: consolidated fact sheet text
      - related_articles: all articles covering this event
    """
    import asyncio
    from app.main import fact_sheet_service
    from app.services.cache_service import cache_get, cache_set, TTL_ANALYSIS

    # Check cache first
    fact_key = f"factsheet:{article_id}"
    cached = cache_get(fact_key)
    if cached:
        return cached

    try:
        result = await asyncio.wait_for(
            fact_sheet_service.generate_fact_sheet(
                article_id=article_id,
                db=db,
            ),
            timeout=15.0,
        )
        # Cache for 1 hour
        cache_set(fact_key, result, TTL_ANALYSIS)
        return result
    except asyncio.TimeoutError:
        logger.warning(f"Fact sheet timed out for {article_id}")
        raise HTTPException(status_code=504, detail="Fact sheet generation timed out.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Fact sheet failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Fact sheet generation failed: {str(e)}")
