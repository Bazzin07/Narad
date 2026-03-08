"""
Fact Sheet Service — aggregates multi-source, multi-language coverage of an event
into a single consolidated fact sheet.

Uses FAISS similarity + entity overlap to find all articles about the same event,
then generates a structured, cross-referenced report.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import Counter

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, Entity, ArticleEntity
from app.services.embedding_service import EmbeddingService
from app.services.entity_service import EntityService
from app.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)


class FactSheetService:
    """
    Given a seed article, finds all related articles covering the same event
    across different sources and languages, then produces a consolidated
    multi-source fact sheet.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        entity_service: EntityService,
        scoring_service: ScoringService,
        llm_service=None,
    ):
        self.embedding = embedding_service
        self.entity = entity_service
        self.scoring = scoring_service
        self.llm = llm_service

    async def generate_fact_sheet(
        self,
        article_id: str,
        db: AsyncSession,
        max_sources: int = 15,
        min_score: float = 0.35,
    ) -> Dict[str, Any]:
        """
        Generate a multi-source fact sheet for a given article.

        1. Retrieve the seed article
        2. Find similar articles via FAISS
        3. Score and filter for high-relevance same-event coverage
        4. Aggregate facts across sources + languages
        5. Optionally use LLM for consolidated narrative
        """
        # 1. Get seed article
        result = await db.execute(select(Article).where(Article.id == article_id))
        seed = result.scalar_one_or_none()
        if not seed:
            raise ValueError(f"Article {article_id} not found")

        # 2. Find FAISS neighbours using embedding service (cosine similarity)
        candidate_pairs = []
        try:
            seed_embedding = self.embedding.generate_embedding(
                f"{seed.title}. {seed.content[:1000]}"
            )
            similar = await self.embedding.find_similar(seed_embedding, k=50)

            # Filter: keep only high-similarity candidates (same-event threshold)
            for aid, cosine_score in similar:
                if aid != article_id and cosine_score >= min_score:
                    candidate_pairs.append((aid, float(cosine_score)))
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")

        # SQL fallback when FAISS has no vectors
        if not candidate_pairs:
            try:
                from datetime import timedelta
                window = timedelta(days=7)
                q = (
                    select(Article)
                    .where(Article.id != article_id)
                    .where(Article.published_at >= (seed.published_at - window))
                    .where(Article.published_at <= (seed.published_at + window))
                    .order_by(Article.published_at.desc())
                )
                if seed.topic and seed.topic != "general":
                    q = q.where(Article.topic == seed.topic)
                q = q.limit(max_sources)
                sql_result = await db.execute(q)
                sql_articles = sql_result.scalars().all()
                for a in sql_articles:
                    candidate_pairs.append((a.id, 0.6))
                logger.info(f"Fact sheet SQL fallback found {len(candidate_pairs)} candidates")
            except Exception as e:
                logger.warning(f"Fact sheet SQL fallback failed: {e}")

        if not candidate_pairs:
            return self._empty_sheet(seed)

        # 3. Fetch candidate articles from DB
        candidate_ids = [c[0] for c in candidate_pairs[:max_sources]]
        faiss_scores = {c[0]: c[1] for c in candidate_pairs}

        result = await db.execute(
            select(Article).where(Article.id.in_(candidate_ids))
        )
        candidates = list(result.scalars().all())

        # 4. Fetch entities for seed + all candidates (single batch query)
        all_ids = [article_id] + [c.id for c in candidates]
        entity_map = await self._get_entity_map(all_ids, db)
        seed_entities = entity_map.get(article_id, set())

        # 5. Build scored list using FAISS cosine similarity directly
        scored_articles = []
        for candidate in candidates:
            score = faiss_scores.get(candidate.id, 0.0)
            candidate_entities = entity_map.get(candidate.id, set())

            scored_articles.append({
                "article": candidate,
                "score": score,
                "shared_entities": seed_entities & candidate_entities,
            })

        # Sort by score (highest = most same-event-like)
        scored_articles.sort(key=lambda x: x["score"], reverse=True)
        scored_articles = scored_articles[:max_sources]

        if not scored_articles:
            return self._empty_sheet(seed)

        # 6. Aggregate cross-source facts
        all_articles_for_sheet = [seed] + [s["article"] for s in scored_articles]
        aggregation = self._aggregate_facts(seed, scored_articles, entity_map)

        # 7. Generate narrative (LLM or rule-based)
        narrative = await self._generate_fact_narrative(seed, scored_articles, aggregation)

        return {
            "seed_article": {
                "id": seed.id,
                "title": seed.title,
                "source": seed.source,
                "language": seed.language,
                "published_at": str(seed.published_at),
                "topic": seed.topic,
                "url": seed.url,
            },
            "coverage": {
                "total_sources": len(set(a.source for a in all_articles_for_sheet)),
                "total_articles": len(all_articles_for_sheet),
                "languages": list(set(a.language or "en" for a in all_articles_for_sheet)),
                "date_range": {
                    "earliest": str(min(a.published_at for a in all_articles_for_sheet)),
                    "latest": str(max(a.published_at for a in all_articles_for_sheet)),
                },
            },
            "key_entities": aggregation["key_entities"],
            "source_perspectives": aggregation["perspectives"],
            "timeline": aggregation["timeline"],
            "narrative": narrative,
            "related_articles": [
                {
                    "id": s["article"].id,
                    "title": s["article"].title,
                    "source": s["article"].source,
                    "language": s["article"].language,
                    "published_at": str(s["article"].published_at),
                    "relevance_score": round(s["score"], 3),
                    "shared_entities": list(s["shared_entities"])[:5],
                    "url": s["article"].url,
                }
                for s in scored_articles
            ],
        }

    def _aggregate_facts(
        self, seed: Article, scored: List[Dict], entity_map: Dict
    ) -> Dict[str, Any]:
        """Aggregate information across all sources covering this event."""
        all_articles = [seed] + [s["article"] for s in scored]

        # Key entities — across all sources
        all_entities: Counter = Counter()
        for article in all_articles:
            for entity in entity_map.get(article.id, set()):
                all_entities[entity] += 1

        key_entities = [
            {"name": name, "mentioned_in": count, "total_sources": len(all_articles)}
            for name, count in all_entities.most_common(15)
        ]

        # Source perspectives — group by source with unique viewpoints
        perspectives = []
        seen_sources = set()
        for article in all_articles:
            if article.source not in seen_sources:
                seen_sources.add(article.source)
                # Extract first 200 chars as the "angle" from this source
                content_snippet = (article.content or "")[:300].strip()
                if len(content_snippet) > 200:
                    content_snippet = content_snippet[:200] + "..."

                perspectives.append({
                    "source": article.source,
                    "language": article.language or "en",
                    "title": article.title,
                    "angle": content_snippet,
                    "published_at": str(article.published_at),
                })

        # Timeline — chronological order of coverage
        timeline = sorted(
            [
                {
                    "source": a.source,
                    "title": a.title,
                    "published_at": str(a.published_at),
                    "language": a.language or "en",
                }
                for a in all_articles
            ],
            key=lambda x: x["published_at"],
        )

        return {
            "key_entities": key_entities,
            "perspectives": perspectives,
            "timeline": timeline,
        }

    async def _generate_fact_narrative(
        self, seed: Article, scored: List[Dict], aggregation: Dict
    ) -> str:
        """Generate a consolidated fact sheet narrative."""
        sources = set([seed.source] + [s["article"].source for s in scored])
        languages = set([seed.language or "en"] + [s["article"].language or "en" for s in scored])
        entities = [e["name"] for e in aggregation["key_entities"][:8]]

        # Build narrative context
        source_summaries = []
        for s in scored[:5]:
            art = s["article"]
            source_summaries.append(
                f"- {art.source} ({art.language}): {art.title}"
            )

        prompt = f"""Generate a consolidated fact sheet for this news event.

SEED ARTICLE: {seed.title}
SOURCE: {seed.source}

COVERAGE: {len(sources)} sources across {len(languages)} languages
KEY ENTITIES: {', '.join(entities)}

OTHER SOURCES COVERING THIS EVENT:
{chr(10).join(source_summaries)}

Write a structured fact sheet with these sections:
1. **Event Summary** — What happened, in 2-3 sentences
2. **Key Facts** — 4-6 bullet points of confirmed facts across sources
3. **Multi-Source Coverage** — How different sources are covering this (1-2 sentences)
4. **Key Players** — People, organizations, and locations involved
5. **Coverage Gap** — What's NOT being covered or what questions remain

Keep it concise, factual, and reference which sources provide which information.
Use hedged language for unconfirmed details."""

        # Try LLM
        if self.llm and hasattr(self.llm, '_invoke_fast'):
            try:
                result = await self.llm._invoke_fast(prompt)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"LLM fact sheet generation failed: {e}")

        # Rule-based fallback
        narrative_parts = [
            f"## Event Summary\n{seed.title}\n",
            f"## Multi-Source Coverage",
            f"This event is covered by **{len(sources)} sources** across **{len(languages)} language(s)**: "
            f"{', '.join(sorted(sources))}.\n",
            f"## Key Entities",
            ", ".join(entities) + "\n" if entities else "No significant entities extracted.\n",
            f"## Source Perspectives",
        ]
        for p in aggregation["perspectives"][:5]:
            narrative_parts.append(f"- **{p['source']}** ({p['language']}): {p['title']}")

        return "\n".join(narrative_parts)

    async def _get_entity_map(self, article_ids: List[str], db: AsyncSession) -> Dict[str, set]:
        """Batch-fetch entities for multiple articles."""
        entity_map: Dict[str, set] = {}
        result = await db.execute(
            select(ArticleEntity.article_id, Entity.normalized_text)
            .join(Entity, ArticleEntity.entity_id == Entity.id)
            .where(ArticleEntity.article_id.in_(article_ids))
        )
        for row in result.fetchall():
            entity_map.setdefault(row[0], set()).add(row[1] or "")
        return entity_map

    def _empty_sheet(self, seed: Article) -> Dict[str, Any]:
        """Return empty fact sheet when no related coverage found."""
        return {
            "seed_article": {
                "id": seed.id,
                "title": seed.title,
                "source": seed.source,
                "language": seed.language,
                "published_at": str(seed.published_at),
                "topic": seed.topic,
                "url": seed.url,
            },
            "coverage": {
                "total_sources": 1,
                "total_articles": 1,
                "languages": [seed.language or "en"],
                "date_range": {
                    "earliest": str(seed.published_at),
                    "latest": str(seed.published_at),
                },
            },
            "key_entities": [],
            "source_perspectives": [],
            "timeline": [],
            "narrative": "No multi-source coverage found for this article in the current corpus.",
            "related_articles": [],
        }
