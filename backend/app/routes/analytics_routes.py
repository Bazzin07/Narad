"""
Analytics Routes — Timeline, Entity Graph, Sentiment Trends, Source Bias.

All features are on-demand (user-triggered), never auto-rendered.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.article import Article, Entity, ArticleEntity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# ── SQL-based related article finder (fallback when FAISS has no embeddings) ──

async def _find_related_sql(seed: Article, db: AsyncSession, limit: int = 15):
    """Find related articles by topic + time window when FAISS is unavailable."""
    from datetime import timedelta
    window = timedelta(days=7)
    q = (
        select(Article)
        .where(Article.id != seed.id)
        .where(Article.published_at >= (seed.published_at - window))
        .where(Article.published_at <= (seed.published_at + window))
        .order_by(Article.published_at.desc())
    )
    if seed.topic and seed.topic != "general":
        q = q.where(Article.topic == seed.topic)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


# ── Timeline View ─────────────────────────────────────────────────────────────

@router.get("/timeline/{article_id}")
async def get_event_timeline(
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a time-ordered sequence of related articles for timeline visualization.
    Uses FAISS similarity when available, falls back to SQL topic/time search.
    """
    from app.main import orchestrator

    # Get seed article
    result = await db.execute(select(Article).where(Article.id == article_id))
    seed = result.scalar_one_or_none()
    if not seed:
        raise HTTPException(status_code=404, detail="Article not found")

    # Try FAISS first, fall back to SQL topic/time search
    articles = []
    similarity_map = {}  # article_id -> similarity score

    emb = orchestrator.embedding.get_embedding_by_id(article_id) if orchestrator.embedding else None
    if emb is not None:
        similar = await orchestrator.embedding.find_similar(emb, k=20)
        candidate_ids = [aid for aid, _ in similar if aid != article_id]
        similarity_map = {aid: s for aid, s in similar}
        if candidate_ids:
            articles_result = await db.execute(
                select(Article).where(Article.id.in_(candidate_ids))
            )
            articles = articles_result.scalars().all()
    
    # SQL fallback when FAISS has no vectors
    if not articles:
        articles = await _find_related_sql(seed, db, limit=20)
        for a in articles:
            similarity_map[a.id] = 0.7  # default similarity for SQL matches

    if not articles:
        return {"seed": _article_summary(seed), "timeline": [], "total_events": 0}

    # Get entities for each article
    entity_map = {}
    for a in articles:
        ent_result = await db.execute(
            select(Entity.text, Entity.type).join(ArticleEntity).where(
                ArticleEntity.article_id == a.id
            )
        )
        entity_map[a.id] = [{"text": r[0], "type": r[1]} for r in ent_result.all()]

    # Build timeline sorted by date
    timeline = []
    for a in articles:
        sim_score = similarity_map.get(a.id, 0.5)
        if sim_score < 0.35:
            continue
        timeline.append({
            "id": a.id,
            "title": a.title,
            "source": a.source,
            "published_at": str(a.published_at),
            "topic": getattr(a, "topic", "general"),
            "sentiment": getattr(a, "sentiment_score", None),
            "key_entities": [e["text"] for e in entity_map.get(a.id, [])[:4]],
            "summary": (a.summary or a.content[:200] + "...") if a.content else "",
            "image_url": getattr(a, "image_url", None),
            "similarity": round(sim_score, 3),
        })

    # Sort by date (oldest first for chronological timeline)
    timeline.sort(key=lambda x: x["published_at"])

    # Include seed at correct position
    seed_entry = {
        "id": seed.id,
        "title": seed.title,
        "source": seed.source,
        "published_at": str(seed.published_at),
        "topic": getattr(seed, "topic", "general"),
        "sentiment": getattr(seed, "sentiment_score", None),
        "key_entities": [],
        "summary": (seed.summary or seed.content[:200] + "...") if seed.content else "",
        "image_url": getattr(seed, "image_url", None),
        "similarity": 1.0,
        "is_seed": True,
    }

    # Insert seed in chronological order
    inserted = False
    for i, t in enumerate(timeline):
        if t["published_at"] > str(seed.published_at):
            timeline.insert(i, seed_entry)
            inserted = True
            break
    if not inserted:
        timeline.append(seed_entry)

    return {
        "seed": _article_summary(seed),
        "timeline": timeline,
        "total_events": len(timeline),
    }





# ── Sentiment Trends ─────────────────────────────────────────────────────────

@router.get("/sentiment/topic/{topic}")
async def get_sentiment_by_topic(
    topic: str,
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """
    Get sentiment trend for a topic over time.
    Compares India vs Global coverage sentiment.
    """
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Fetch articles for this topic
    result = await db.execute(
        select(
            func.date(Article.published_at).label("date"),
            Article.geographic_scope,
            func.avg(Article.sentiment_score).label("avg_sentiment"),
            func.count(Article.id).label("count"),
        )
        .where(Article.topic == topic)
        .where(Article.published_at >= cutoff)
        .where(Article.sentiment_score.isnot(None))
        .group_by(func.date(Article.published_at), Article.geographic_scope)
        .order_by(func.date(Article.published_at))
    )
    rows = result.all()

    trend_india = []
    trend_global = []
    for date_val, scope, avg_sent, count in rows:
        entry = {
            "date": str(date_val),
            "sentiment": round(float(avg_sent), 3) if avg_sent else 0,
            "count": count,
        }
        if scope in ("india", "mixed"):
            trend_india.append(entry)
        else:
            trend_global.append(entry)

    return {
        "topic": topic,
        "days": days,
        "india_trend": trend_india,
        "global_trend": trend_global,
    }


@router.get("/sentiment/entity/{entity_name}")
async def get_sentiment_by_entity(
    entity_name: str,
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """Get sentiment trend for articles mentioning a specific entity."""
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Article.published_at).label("date"),
            func.avg(Article.sentiment_score).label("avg_sentiment"),
            func.count(Article.id).label("count"),
        )
        .join(ArticleEntity, Article.id == ArticleEntity.article_id)
        .join(Entity, ArticleEntity.entity_id == Entity.id)
        .where(
            func.lower(Entity.normalized_text).contains(entity_name.lower())
        )
        .where(Article.published_at >= cutoff)
        .where(Article.sentiment_score.isnot(None))
        .group_by(func.date(Article.published_at))
        .order_by(func.date(Article.published_at))
    )
    rows = result.all()

    return {
        "entity": entity_name,
        "days": days,
        "trend": [
            {"date": str(d), "sentiment": round(float(s), 3) if s else 0, "count": c}
            for d, s, c in rows
        ],
    }


# ── Source Bias Analysis ──────────────────────────────────────────────────────

@router.post("/bias/{article_id}")
async def get_source_bias_analysis(
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Compare how different sources frame the same event.
    Retrieves 3-5 articles about the same event from different sources,
    analyzes differences in sentiment, entity emphasis, and tone.
    LLM generates structured comparison ONLY after deterministic grouping.
    """
    from app.main import orchestrator
    from app.services.sentiment_service import compute_sentiment, sentiment_label

    # Get seed article
    result = await db.execute(select(Article).where(Article.id == article_id))
    seed = result.scalar_one_or_none()
    if not seed:
        raise HTTPException(status_code=404, detail="Article not found")

    # Find similar articles from different sources — FAISS preferred, SQL fallback
    articles = []
    similarity_map = {}

    emb = orchestrator.embedding.get_embedding_by_id(article_id) if orchestrator.embedding else None
    if emb is not None:
        similar = await orchestrator.embedding.find_similar(emb, k=20)
        candidate_ids = [aid for aid, s in similar if s > 0.50 and aid != article_id]
        similarity_map = {aid: s for aid, s in similar}
        if candidate_ids:
            articles_result = await db.execute(
                select(Article).where(Article.id.in_(candidate_ids))
            )
            articles = articles_result.scalars().all()

    # SQL fallback when FAISS has no vectors
    if not articles:
        articles = await _find_related_sql(seed, db, limit=20)
        for a in articles:
            similarity_map[a.id] = 0.7

    # Pick up to 5 from different sources
    seen_sources = {seed.source.lower()}
    selected = []
    for a in sorted(articles, key=lambda x: similarity_map.get(x.id, 0), reverse=True):
        src_key = a.source.lower()
        if src_key not in seen_sources:
            seen_sources.add(src_key)
            selected.append(a)
        if len(selected) >= 5:
            break

    if not selected:
        return {"seed": _article_summary(seed), "comparisons": [], "narrative": "No alternative source coverage found.", "total_sources": 1}

    # Analyze each source's framing
    comparisons = []
    for a in selected:
        sim_score = next((s for aid, s in similar if aid == a.id), 0)
        sent = getattr(a, "sentiment_score", None) or compute_sentiment(a.title, a.content)

        # Get entities for emphasis analysis
        ent_result = await db.execute(
            select(Entity.text, Entity.type).join(ArticleEntity).where(ArticleEntity.article_id == a.id)
        )
        entities = [{"text": r[0], "type": r[1]} for r in ent_result.all()]

        comparisons.append({
            "id": a.id,
            "title": a.title,
            "source": a.source,
            "language": a.language,
            "published_at": str(a.published_at),
            "sentiment": sent,
            "sentiment_label": sentiment_label(sent),
            "key_entities": [e["text"] for e in entities[:8]],
            "similarity": round(sim_score, 3),
        })

    # Get seed entities for comparison
    seed_ent_result = await db.execute(
        select(Entity.text).join(ArticleEntity).where(ArticleEntity.article_id == seed.id)
    )
    seed_entities = [r[0] for r in seed_ent_result.all()]

    # Generate LLM bias analysis (optional — falls back gracefully)
    narrative = ""
    try:
        llm = orchestrator.llm
        if hasattr(llm, '_invoke_fast'):
            seed_sent = getattr(seed, "sentiment_score", None) or compute_sentiment(seed.title, seed.content)
            prompt = f"""You are a media analysis expert. Compare how different news sources cover the same event.

== ORIGINAL ARTICLE ==
Source: {seed.source}
Title: {seed.title}
Sentiment: {sentiment_label(seed_sent)} ({seed_sent:.2f})
Key entities: {', '.join(seed_entities[:6])}

== ALTERNATIVE SOURCES ==
"""
            for c in comparisons:
                prompt += f"""
Source: {c['source']} ({c['language']})
Title: {c['title']}
Sentiment: {c['sentiment_label']} ({c['sentiment']:.2f})
Key entities: {', '.join(c['key_entities'][:6])}
"""
            prompt += """
== YOUR ANALYSIS ==
Provide a brief structured comparison:
1. **Common Facts** — What all sources agree on
2. **Differences in Emphasis** — What each source highlights differently
3. **Tone Difference** — How the emotional framing varies
4. **Possible Framing Bias** — Any notable bias patterns

Keep it concise (150 words max). Be factual and objective."""

            narrative = await llm._invoke_fast(prompt) or ""
    except Exception as e:
        logger.warning(f"LLM bias analysis failed: {e}")

    if not narrative:
        narrative = _fallback_bias_narrative(seed, comparisons)

    return {
        "seed": {
            **_article_summary(seed),
            "sentiment": getattr(seed, "sentiment_score", None),
            "key_entities": seed_entities[:8],
        },
        "comparisons": comparisons,
        "narrative": narrative,
        "total_sources": len(comparisons) + 1,
    }


# ── Sentiment Backfill ────────────────────────────────────────────────────────

@router.post("/backfill-sentiment")
async def backfill_sentiment(
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Backfill sentiment scores for existing articles that don't have one."""
    from app.services.sentiment_service import compute_sentiment

    result = await db.execute(
        select(Article).where(Article.sentiment_score.is_(None)).limit(limit)
    )
    articles = result.scalars().all()

    updated = 0
    for a in articles:
        a.sentiment_score = compute_sentiment(a.title, a.content)
        updated += 1

    await db.commit()
    logger.info(f"Backfilled sentiment for {updated} articles")
    return {"updated": updated, "remaining": "run again if more exist"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _article_summary(article: Article) -> dict:
    return {
        "id": article.id,
        "title": article.title,
        "source": article.source,
        "published_at": str(article.published_at),
        "topic": getattr(article, "topic", "general"),
        "image_url": getattr(article, "image_url", None),
    }


def _fallback_bias_narrative(seed, comparisons):
    """Rule-based fallback when LLM is unavailable for bias analysis."""
    parts = [f"**{seed.source}** reported: \"{seed.title}\""]

    sentiments = {"Positive": [], "Negative": [], "Neutral": []}
    from app.services.sentiment_service import sentiment_label
    seed_sent = getattr(seed, "sentiment_score", 0) or 0
    sentiments[sentiment_label(seed_sent)].append(seed.source)
    for c in comparisons:
        sentiments[c["sentiment_label"]].append(c["source"])
        parts.append(f"**{c['source']}** framed it as: \"{c['title']}\"")

    tone_summary = []
    for label, sources in sentiments.items():
        if sources:
            tone_summary.append(f"{label}: {', '.join(sources)}")

    return "\n\n".join(parts) + "\n\n**Tone distribution:** " + " | ".join(tone_summary)
