"""
Orchestrator Service — coordinates the full pipeline.

Three user-facing features:
  1. Deep Analysis — detailed breakdown of a single news event
  2. Impact Analysis — how two events from different domains affect each other
  3. News Probe — user submits text, system finds related articles and explains connections

Pipeline: Ingest → Extract Entities → Embed → Cluster → Score → Validate → LLM
"""
import logging
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, BedrockCall
from app.services.ingestion_service import _sanitize_content
from app.models.schemas import (
    ArticleSummary, ArticleDetail, CompareResponse,
    RelationScoreSchema, ValidationResultSchema,
    ProbeResponse, ProbeMatchSchema,
)
from app.services.scoring_service import ScoringService
from app.services.validation_service import ValidationService
from app.services.llm_service import LLMService
from app.services.entity_service import EntityService
from app.services.embedding_service import EmbeddingService
from app.services.clustering_service import ClusteringService
from app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

# Import cache functions
from app.services.cache_service import (
    cache_get, cache_set, feed_key, article_key, analysis_key,
    TTL_FEED, TTL_ARTICLE, TTL_ANALYSIS,
)


class Orchestrator:
    """Top-level coordinator — ties all services together."""

    def __init__(
        self,
        ingestion_service: IngestionService,
        entity_service: EntityService,
        embedding_service: EmbeddingService,
        clustering_service: ClusteringService,
        scoring_service: ScoringService,
        validation_service: ValidationService,
        llm_service: LLMService,
    ):
        self.ingestion = ingestion_service
        self.entity = entity_service
        self.embedding = embedding_service
        self.clustering = clustering_service
        self.scoring = scoring_service
        self.validation = validation_service
        self.llm = llm_service

    # ── News Listing ──────────────────────────────────────────────────────────

    async def get_recent_news(
        self, db: AsyncSession, limit: int = 20, offset: int = 0,
        language: Optional[str] = None, region: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[ArticleSummary]:
        """Return recent articles, optionally filtered by language, region, and state.
        
        v2: Uses batch queries instead of N+1 for entities and clusters.
        v3: Excludes YouTube/Reddit (social) articles from the feed.
        v4: Supports region filtering (india/global) for India-focused homepage.
        v5: Supports state-level filtering for India Command Center.
        """
        from app.models.article import Source as SourceModel

        # 1. Fetch articles — exclude social sources (YouTube/Reddit) from feed
        query = (
            select(Article)
            .outerjoin(SourceModel, Article.source_id == SourceModel.id)
            .where(
                (SourceModel.source_type != "social") | (Article.source_id.is_(None))
            )
            .order_by(desc(Article.published_at))
        )

        # Region filter — content-based geographic scope (not just source region)
        if region == "india":
            # India feed: show articles WITH India relevance (india + mixed)
            query = query.where(
                Article.geographic_scope.in_(["india", "mixed"])
            )
        elif region == "global":
            # Global/World feed: show only purely international articles
            query = query.where(
                Article.geographic_scope == "global"
            )
        elif region:
            # Fallback: legacy source_region filter
            query = query.where(SourceModel.source_region == region)

        # State filter — for India Command Center
        if state:
            query = query.where(Article.state == state)

        if language:
            query = query.where(Article.language == language)

        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        articles = result.scalars().all()

        if not articles:
            return []

        article_ids = [a.id for a in articles]

        # 2. Batch fetch all entities for these articles (single query)
        from app.models.article import Entity, ArticleEntity
        entity_result = await db.execute(
            select(ArticleEntity.article_id, Entity.text, Entity.type)
            .join(Entity, ArticleEntity.entity_id == Entity.id)
            .where(ArticleEntity.article_id.in_(article_ids))
        )
        entity_map: Dict[str, List[dict]] = {aid: [] for aid in article_ids}
        for row in entity_result.fetchall():
            entity_map[row[0]].append({"text": row[1], "type": row[2]})

        # 3. Batch fetch all cluster assignments (single query)
        from app.models.article import ArticleCluster
        cluster_result = await db.execute(
            select(ArticleCluster.article_id, ArticleCluster.cluster_id)
            .where(ArticleCluster.article_id.in_(article_ids))
        )
        cluster_map: Dict[str, Optional[int]] = {aid: None for aid in article_ids}
        for row in cluster_result.fetchall():
            cluster_map[row[0]] = row[1]

        # 4. Assemble summaries (no more DB calls)
        summaries = []
        for a in articles:
            entities = entity_map.get(a.id, [])
            cluster_id = cluster_map.get(a.id)

            summaries.append(ArticleSummary(
                id=a.id,
                title=a.title,
                source=a.source,
                published_at=str(a.published_at),
                language=getattr(a, 'language', 'en'),
                entities=[e["text"] for e in entities],
                cluster_id=cluster_id,
                image_url=getattr(a, 'image_url', None),
                topic=getattr(a, 'topic', None),
            ))

        return summaries

    async def get_article_detail(self, article_id: str, db: AsyncSession) -> Optional[ArticleDetail]:
        """Get full article details. Cached for 10 minutes."""
        # Check cache
        ck = article_key(article_id)
        cached = cache_get(ck)
        if cached:
            return ArticleDetail(**cached)

        result = await db.execute(select(Article).where(Article.id == article_id))
        article = result.scalar_one_or_none()
        if not article:
            return None

        entities = await self.entity.get_article_entities(article_id, db)
        cluster_id = await self.clustering.get_article_cluster(article_id, db)

        detail = ArticleDetail(
            id=article.id,
            title=article.title,
            content=_sanitize_content(article.content),
            summary=_sanitize_content(article.summary),
            source=article.source,
            url=article.url,
            published_at=str(article.published_at),
            entities=entities,
            cluster_id=cluster_id,
            processed=article.processed,
            image_url=getattr(article, 'image_url', None),
            topic=getattr(article, 'topic', None),
        )

        # Cache the result
        cache_set(ck, detail.model_dump(), TTL_ARTICLE)

        return detail

    # ── Feature 1: Deep Analysis ──────────────────────────────────────────────

    async def analyze_article(
        self, article_id: str, session_id: str, db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Deep analysis of a single news event.
        Returns detailed breakdown with context and implications.
        Uses 1 Bedrock call.
        """
        # Fetch article
        result = await db.execute(select(Article).where(Article.id == article_id))
        article = result.scalar_one_or_none()
        if not article:
            raise ValueError("Article not found")

        # Get entities and cluster info
        entities = await self.entity.get_article_entities(article_id, db)
        cluster_id = await self.clustering.get_article_cluster(article_id, db)

        # Build cluster context
        cluster_info = None
        if cluster_id:
            members = await self.clustering.get_cluster_members(cluster_id, db)
            other_count = len(members) - 1
            if other_count > 0:
                cluster_info = f"{other_count} other related articles are covering this same story"

        # Validate LLM call
        validation = self.validation.validate_llm_call(0.80, session_id)  # Deep analysis always qualifies

        # Generate analysis
        article_dict = {
            "title": article.title,
            "content": _sanitize_content(article.content),
            "summary": _sanitize_content(article.summary),
            "source": article.source,
            "published_at": str(article.published_at),
        }

        if validation.allowed:
            analysis = await self.llm.generate_deep_analysis(
                article_dict, entities, cluster_info
            )
            self.validation.track_call(session_id)

            # Record the call
            bedrock_call = BedrockCall(
                session_id=session_id,
                article1_id=article_id,
                article2_id=None,
                relation_score=0.80,
                explanation=analysis,
            )
            db.add(bedrock_call)
            await db.commit()
        else:
            analysis = self.llm.fallback_deep_analysis(
                article_dict, entities, cluster_info
            )

        # Find related articles from same cluster
        related = []
        if cluster_id:
            members = await self.clustering.get_cluster_members(cluster_id, db)
            for mid in members:
                if mid != article_id:
                    r = await db.execute(select(Article).where(Article.id == mid))
                    rel_article = r.scalar_one_or_none()
                    if rel_article:
                        related.append({
                            "id": rel_article.id,
                            "title": rel_article.title,
                            "source": rel_article.source,
                            "published_at": str(rel_article.published_at),
                        })

        return {
            "article": {
                "id": article.id,
                "title": article.title,
                "content": article.content,
                "source": article.source,
                "url": article.url,
                "published_at": str(article.published_at),
            },
            "entities": [{"text": e["text"], "type": e["type"]} for e in entities],
            "analysis": analysis,
            "related_articles": related[:5],
            "cluster_id": cluster_id,
            "validation": {
                "llm_used": validation.allowed,
                "calls_remaining": validation.calls_remaining - (1 if validation.allowed else 0),
            },
        }

    # ── Feature 2: Impact Analysis ────────────────────────────────────────────

    async def compare_events(
        self,
        article1_id: str,
        article2_id: str,
        session_id: str,
        db: AsyncSession,
        preferred_language: str = "English",
        detailed: bool = False,
    ) -> CompareResponse:
        """
        Cross-domain impact analysis between two events.

        Two tiers:
          - Overview (default): quick summary of how they connect, with sources
          - Detailed: full deep analysis with cause-effect chains and implications
        """
        # 1. Fetch articles
        r1 = await db.execute(select(Article).where(Article.id == article1_id))
        r2 = await db.execute(select(Article).where(Article.id == article2_id))
        article1 = r1.scalar_one_or_none()
        article2 = r2.scalar_one_or_none()

        if not article1 or not article2:
            raise ValueError("One or both articles not found")

        # 2. Run deterministic scoring
        score = await self.scoring.calculate_relation_score(
            article1_id, article2_id, db,
            article1=article1, article2=article2,
        )

        # 3. Get shared entities
        shared = await self.entity.get_shared_entities(article1_id, article2_id, db)

        # 4. Validate before LLM call
        validation = self.validation.validate_llm_call(score.total_score, session_id)

        # 5. Build article dicts
        article1_dict = {
            "title": article1.title,
            "content": article1.content,
            "summary": article1.summary,
            "source": article1.source,
            "published_at": str(article1.published_at),
        }
        article2_dict = {
            "title": article2.title,
            "content": article2.content,
            "summary": article2.summary,
            "source": article2.source,
            "published_at": str(article2.published_at),
        }

        # 6. TIER 1 — Always generate the overview
        overview = None
        if score.total_score >= 0.30:
            overview = self.llm.overview_analysis(
                score, shared, article1_dict, article2_dict
            )

        # 7. TIER 2 — Deep analysis only when detailed=True
        explanation = None
        if detailed:
            if validation.allowed:
                explanation = await self.llm.generate_impact_analysis(
                    article1_dict, article2_dict, score, shared,
                    preferred_language=preferred_language,
                )
                self.validation.track_call(session_id)

                bedrock_call = BedrockCall(
                    session_id=session_id,
                    article1_id=article1_id,
                    article2_id=article2_id,
                    relation_score=score.total_score,
                    explanation=explanation,
                )
                db.add(bedrock_call)
                await db.flush()
            elif score.total_score >= 0.35:
                explanation = self.llm.fallback_impact_analysis(
                    score, shared, article1_dict, article2_dict
                )

        # 8. Build article summaries
        entities1 = await self.entity.get_article_entities(article1_id, db)
        entities2 = await self.entity.get_article_entities(article2_id, db)
        c1 = await self.clustering.get_article_cluster(article1_id, db)
        c2 = await self.clustering.get_article_cluster(article2_id, db)

        summary1 = ArticleSummary(
            id=article1.id, title=article1.title, source=article1.source,
            published_at=str(article1.published_at),
            entities=[e["text"] for e in entities1], cluster_id=c1,
        )
        summary2 = ArticleSummary(
            id=article2.id, title=article2.title, source=article2.source,
            published_at=str(article2.published_at),
            entities=[e["text"] for e in entities2], cluster_id=c2,
        )

        await db.commit()

        return CompareResponse(
            article1=summary1,
            article2=summary2,
            relation_score=RelationScoreSchema(
                total_score=score.total_score,
                confidence=score.confidence,
                embedding_similarity=score.embedding_similarity,
                entity_overlap=score.entity_overlap,
                temporal_proximity=score.temporal_proximity,
                source_diversity=score.source_diversity,
                graph_distance=score.graph_distance,
                credibility_factor=score.credibility_factor,
            ),
            shared_entities=[e["text"] for e in shared],
            overview=overview,
            explanation=explanation,
            validation=ValidationResultSchema(
                allowed=validation.allowed,
                reason=validation.reason,
                score=validation.score,
                calls_remaining=validation.calls_remaining,
            ),
        )

    # ── Processing Pipeline ───────────────────────────────────────────────────

    async def run_full_pipeline(self, db: AsyncSession) -> dict:
        """
        Run the full ingestion → extraction → embedding → clustering pipeline.
        No LLM calls. Fully deterministic.
        """
        results = {}

        # 1. Ingest
        ingest_result = await self.ingestion.run_ingestion(db)
        results["ingestion"] = ingest_result

        # 2. Entity extraction (loop until all done)
        total_entities = 0
        while True:
            batch = await self.entity.process_unprocessed(db, limit=100)
            total_entities += batch
            if batch == 0:
                break
        results["entities_processed"] = total_entities

        # 3. Embeddings (loop until all done)
        total_embeddings = 0
        while True:
            batch = await self.embedding.process_unprocessed(db, limit=100)
            total_embeddings += batch
            if batch == 0:
                break
        results["embeddings_processed"] = total_embeddings

        # 4. Clustering
        clusters = await self.clustering.cluster_articles(db)
        results["clusters_found"] = len(clusters)

        logger.info(f"Full pipeline complete: {results}")
        return results

    # ── Feature 3: News Probe ─────────────────────────────────────────────────

    async def probe_news(
        self,
        text: str,
        source: str,
        session_id: str,
        db: AsyncSession,
        preferred_language: str = "English",
        top_k: int = 5,
        detailed: bool = False,
    ) -> ProbeResponse:
        """
        Feature 3: News Probe — user submits any news text and
        Narad finds related articles from the corpus and explains
        how they are connected.

        Two tiers:
          - Overview (default): connection map + quick per-match summaries
          - Detailed: full deep analysis per match with cause-effect chains
        """
        from app.services.ingestion_service import _detect_language

        # 1. Detect language
        detected_lang = _detect_language(text)
        logger.info(f"Probe: detected language={detected_lang}, source={source}")

        # 2. Extract entities from the user's text
        probe_entities = self.entity.extract_entities(text, language=detected_lang)
        entity_names = list({e[0] for e in probe_entities})  # (text, type, normalized)
        entity_normalized = {e[2] for e in probe_entities if len(e[2]) >= 3}  # normalized forms
        logger.info(f"Probe: extracted {len(entity_names)} entities: {entity_names[:10]}")

        # 3. Embed the user's text
        probe_embedding = self.embedding.generate_embedding(text)

        # 4. FAISS search for similar articles
        candidates = await self.embedding.find_similar(probe_embedding, k=min(top_k * 3, 30))
        logger.info(f"Probe: FAISS returned {len(candidates)} candidates")

        if not candidates:
            return ProbeResponse(
                query_text=text[:500],
                query_source=source,
                detected_language=detected_lang,
                extracted_entities=entity_names,
                matches=[],
                total_matches_found=0,
                overview_map="No related articles found in the corpus.",
                analysis_summary="No related articles found in the corpus.",
            )

        # 5. Score each candidate
        matches: List[dict] = []
        for article_id, faiss_score in candidates:
            # Fetch article
            result = await db.execute(select(Article).where(Article.id == article_id))
            article = result.scalar_one_or_none()
            if not article:
                continue

            # Embedding similarity (recompute for accuracy)
            article_emb = self.embedding.get_embedding_by_id(article_id)
            if article_emb is not None:
                emb_sim = float(self.embedding.cosine_similarity(probe_embedding, article_emb))
            else:
                emb_sim = float(faiss_score)

            # Entity overlap — match probe entities against article entities
            article_entities = await self.entity.get_article_entities(article_id, db)
            article_normalized = {e["normalized"] for e in article_entities if len(e["normalized"]) >= 3}

            shared_entity_texts = []
            if entity_normalized and article_normalized:
                from app.services.entity_service import fuzzy_match
                matched_art = set()
                for pn in entity_normalized:
                    for an in article_normalized:
                        if an not in matched_art and fuzzy_match(pn, an):
                            display = next(
                                (e["text"] for e in article_entities if e["normalized"] == an),
                                an
                            )
                            shared_entity_texts.append(display)
                            matched_art.add(an)
                            break

            ent_overlap_score = 0.0
            total_entities = len(entity_normalized | article_normalized)
            if total_entities > 0:
                ent_overlap_score = len(shared_entity_texts) / total_entities

            # Temporal proximity (probe is "now")
            now = datetime.utcnow()
            hours_diff = abs((now - article.published_at).total_seconds()) / 3600
            temp_score = max(0.0, 1.0 - (hours_diff / 168))  # decays over 1 week

            # Source diversity
            src_div = 1.0 if source.lower() != article.source.lower() else 0.5

            # Graph/cluster distance
            cluster_id = await self.clustering.get_article_cluster(article_id, db)
            graph_dist = 0.5  # probe text has no cluster, neutral

            # Credibility
            user_cred = 0.6
            art_cred = getattr(article, 'credibility_weight', 1.0) or 1.0
            avg_cred = (user_cred + art_cred) / 2.0

            # Weighted composite
            raw_score = (
                0.35 * emb_sim
                + 0.25 * ent_overlap_score
                + 0.15 * temp_score
                + 0.15 * src_div
                + 0.10 * graph_dist
            )
            final_score = round(max(0.0, min(1.0, raw_score * avg_cred)), 4)

            from app.services.scoring_service import classify_confidence
            confidence = classify_confidence(final_score)

            matches.append({
                "article": article,
                "article_entities": article_entities,
                "cluster_id": cluster_id,
                "score": final_score,
                "confidence": confidence,
                "emb_sim": round(emb_sim, 4),
                "ent_overlap": round(ent_overlap_score, 4),
                "temp_score": round(temp_score, 4),
                "src_div": round(src_div, 4),
                "graph_dist": round(graph_dist, 4),
                "credibility": round(avg_cred, 4),
                "shared_entities": shared_entity_texts,
            })

        # Sort by score descending, take top_k
        matches.sort(key=lambda m: m["score"], reverse=True)
        matches = matches[:top_k]

        # 6. Build response — two-tier
        probe_dict = {
            "title": text[:100],
            "content": text,
            "summary": text[:500],
            "source": source,
            "published_at": str(datetime.utcnow()),
        }

        response_matches = []
        for m in matches:
            article = m["article"]
            article_dict = {
                "title": article.title,
                "content": article.content,
                "summary": article.summary,
                "source": article.source,
                "published_at": str(article.published_at),
            }

            from app.services.scoring_service import RelationScore
            rel_score = RelationScore(
                total_score=m["score"],
                confidence=m["confidence"],
                embedding_similarity=m["emb_sim"],
                entity_overlap=m["ent_overlap"],
                temporal_proximity=m["temp_score"],
                source_diversity=m["src_div"],
                graph_distance=m["graph_dist"],
                credibility_factor=m["credibility"],
            )

            explanation = None
            if detailed and m["score"] >= 0.35:
                # TIER 2: full deep analysis per match
                explanation = self.llm.fallback_impact_analysis(
                    rel_score, [{"text": e} for e in m["shared_entities"]],
                    probe_dict, article_dict
                )
            elif not detailed and m["score"] >= 0.30:
                # TIER 1: quick overview per match
                explanation = self.llm.overview_analysis(
                    rel_score, [{"text": e} for e in m["shared_entities"]],
                    probe_dict, article_dict
                )

            summary = ArticleSummary(
                id=article.id,
                title=article.title,
                source=article.source,
                published_at=str(article.published_at),
                language=article.language,
                entities=[e["text"] for e in m["article_entities"]],
                cluster_id=m["cluster_id"],
            )

            response_matches.append(ProbeMatchSchema(
                article=summary,
                relation_score=RelationScoreSchema(
                    total_score=m["score"],
                    confidence=m["confidence"],
                    embedding_similarity=m["emb_sim"],
                    entity_overlap=m["ent_overlap"],
                    temporal_proximity=m["temp_score"],
                    source_diversity=m["src_div"],
                    graph_distance=m["graph_dist"],
                    credibility_factor=m["credibility"],
                ),
                shared_entities=m["shared_entities"],
                explanation=explanation,
            ))

        # Generate overview map (always)
        overview_map = self.llm.overview_probe_summary(
            query_text=text,
            query_source=source,
            matches=matches,
            probe_entities=entity_names,
        )

        # Build analysis summary
        if response_matches:
            analysis_summary = await self.llm.generate_probe_summary(
                query_text=text,
                query_source=source,
                matches=matches,
                preferred_language=preferred_language
            )
        else:
            analysis_summary = "No closely related articles were found."

        return ProbeResponse(
            query_text=text[:500],
            query_source=source,
            detected_language=detected_lang,
            extracted_entities=entity_names[:20],
            matches=response_matches,
            total_matches_found=len(response_matches),
            overview_map=overview_map,
            analysis_summary=analysis_summary,
        )

