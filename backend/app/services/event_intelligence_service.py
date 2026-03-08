"""
Event Intelligence Service — On-demand multi-event relationship analysis.

Goes beyond simple similarity chains. Given a seed article, this service:
  1. Retrieves a broad candidate set (FAISS neighbours + entity-linked articles)
  2. Evaluates multi-signal relationships across the candidate network
  3. Groups candidates into a coherent event narrative cluster
  4. Generates a structured explanation of how events connect

Three-component output:
  - Relevant articles with connection metadata
  - Structured narrative explaining the event network
  - Confidence assessment (Strong / Moderate / Speculative)

Key principles:
  - Analytical insights, not causal assertions
  - Cross-domain pattern detection (security → economics → politics, etc.)
  - Hedged language — "possible connection" not "caused by"
"""
import logging
import math
from collections import defaultdict
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, Entity, ArticleEntity, ArticleCluster
from app.services.embedding_service import EmbeddingService
from app.services.entity_service import EntityService
from app.services.scoring_service import ScoringService
from app.services.clustering_service import ClusteringService
from app.services.llm_service import LLMService
from app.services.ingestion_service import _sanitize_content

logger = logging.getLogger(__name__)

# ── Domain mapping for cross-domain analysis ──────────────────────────────────

DOMAIN_MAP = {
    "military": "security", "terrorism": "security",
    "diplomacy": "geopolitics", "politics": "geopolitics",
    "economy": "economics", "energy": "economics", "business": "economics",
    "technology": "technology", "health": "social", "education": "social",
    "environment": "environment", "general": "general",
}

# Known causal transition pathways between domains
CAUSAL_PATHWAYS = {
    ("security", "geopolitics"), ("security", "economics"),
    ("geopolitics", "economics"), ("economics", "social"),
    ("economics", "environment"), ("geopolitics", "social"),
    ("technology", "economics"), ("technology", "security"),
    ("environment", "economics"), ("environment", "social"),
}


def _domain(topic: Optional[str]) -> str:
    return DOMAIN_MAP.get((topic or "general").lower(), "general")


def _is_pathway(d1: str, d2: str) -> bool:
    pair = tuple(sorted([d1, d2]))
    return pair in CAUSAL_PATHWAYS or (pair[1], pair[0]) in CAUSAL_PATHWAYS


# ── Narrative generation prompt ───────────────────────────────────────────────

EVENT_NETWORK_PROMPT = """You are a world-class intelligence analyst writing for a general audience.

You have been given a primary news event and {n_related} potentially related events that were identified through entity overlap, semantic similarity, temporal proximity, and topic analysis.

Your task is to analyze whether these events form a meaningful pattern or narrative — not just whether they're similar, but how they might connect through cause-and-effect chains, shared actors, policy consequences, or cascading impacts across domains.

== PRIMARY EVENT ==
Title: {seed_title}
Source: {seed_source}
Published: {seed_published}
Content: {seed_content}

== RELATED EVENTS ==
{related_events_text}

== CONNECTION SIGNALS ==
{signals_summary}

== YOUR ANALYSIS ==

Provide a structured analysis with these sections:

1. **Event Network Overview** — Describe the cluster of events in 3-4 sentences. What broader story or pattern emerges from these events together?

2. **How These Events Connect** — For the most significant connections, explain the actual mechanism: How does Event A lead to or influence Event B? What are the intermediate steps? Be specific about the chain of cause and effect.

3. **Cross-Domain Impacts** — If events span different domains (e.g., military → economic, diplomatic → social), explain the cross-domain ripple effects. How do actions in one sphere cascade into consequences in another?

4. **Emerging Patterns** — What broader trends or patterns does this event network reveal? Are there early warning signals or developing situations that haven't fully materialized yet?

5. **What To Watch** — Based on the connections identified, what should people pay attention to next? What would confirm or contradict the patterns identified?

IMPORTANT GUIDELINES:
- Use hedged language: "suggests", "may indicate", "potentially connected", "appears to be related"
- Never assert definitive causality — present analytical possibilities
- Be specific about HOW events connect, not just THAT they connect
- Highlight the most surprising or non-obvious connections
- If some connections are speculative, clearly label them as such
- If the connection signals are weak (low scores, few shared entities), CLEARLY STATE that no strong relationship was detected and the connection is uncertain
- Do NOT fabricate or invent causal relationships that are not supported by the provided signals
- Write in {output_language}
"""


class EventIntelligenceService:
    """
    On-demand event relationship analysis.
    Discovers multi-event narratives from a seed article.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        entity_service: EntityService,
        scoring_service: ScoringService,
        clustering_service: ClusteringService,
        llm_service: LLMService,
    ):
        self.embedding = embedding_service
        self.entity = entity_service
        self.scoring = scoring_service
        self.clustering = clustering_service
        self.llm = llm_service

    async def explore_connections(
        self,
        seed_article_id: str,
        db: AsyncSession,
        max_candidates: int = 25,
        min_relevance: float = 0.50,
        preferred_language: str = "English",
    ) -> Dict[str, Any]:
        """
        Main entry point: explore event connections around a seed article.

        Returns:
          - related_events: list of connected articles with metadata
          - narrative: LLM-generated structured explanation
          - confidence: overall assessment (Strong / Moderate / Speculative)
          - signals_summary: breakdown of what signals were found
        """
        # 1. Fetch seed article
        result = await db.execute(select(Article).where(Article.id == seed_article_id))
        seed = result.scalar_one_or_none()
        if not seed:
            raise ValueError(f"Article {seed_article_id} not found")

        # 2. Retrieve broad candidate set
        candidates = await self._retrieve_candidates(seed, seed_article_id, db, max_candidates)
        if not candidates:
            return self._empty_result(seed_article_id, seed)

        # 3. Batch-fetch all candidate articles + metadata
        candidate_ids = list(candidates.keys())
        articles, entity_map, cluster_map = await self._batch_fetch(
            [seed_article_id] + candidate_ids, seed, db
        )

        # 4. Score all candidates against seed using multi-signal analysis
        scored_candidates = self._score_candidates(
            seed_article_id, seed, candidate_ids, candidates,
            articles, entity_map, cluster_map
        )

        # 5. Filter and rank — multi-stage filtering to prevent false connections
        relevant = []
        for c in scored_candidates:
            if c["relevance_score"] < min_relevance:
                continue
            # Hard filter: must have minimum embedding OR entity overlap
            # This prevents weak composite scores from sneaking through
            signals = c.get("signals", {})
            emb = signals.get("embedding", 0)
            ent = signals.get("entity_overlap", 0)
            # Accept if: embedding >= 0.30 OR entity_overlap >= 0.20
            if emb < 0.30 and ent < 0.20:
                continue
            relevant.append(c)

        relevant.sort(key=lambda c: c["relevance_score"], reverse=True)

        # Take top 12 for narrative generation
        top_events = relevant[:12]

        if not top_events:
            return self._no_meaningful_result(seed_article_id, seed, len(candidates))

        # 5b. LLM Validation Layer — validate top-3 connections
        #     Only top-3 to keep LLM costs minimal
        validated_events = []
        for i, e in enumerate(top_events):
            if i < 3 and hasattr(self.llm, 'validate_connection'):
                art = articles.get(e["article_id"])
                if art:
                    a1 = {"title": seed.title, "source": seed.source}
                    a2 = {"title": art.title, "source": art.source}
                    # Build a mock score object for validation
                    from app.services.scoring_service import RelationScore, classify_confidence
                    signals = e.get("signals", {})
                    mock_score = RelationScore(
                        total_score=e["relevance_score"],
                        confidence=classify_confidence(e["relevance_score"]),
                        embedding_similarity=signals.get("embedding", 0),
                        entity_overlap=signals.get("entity_overlap", 0),
                        temporal_proximity=signals.get("temporal", 0),
                        source_diversity=signals.get("source_div", 0),
                        graph_distance=signals.get("cluster", 0),
                    )
                    try:
                        verdict = await self.llm.validate_connection(
                            a1, a2, mock_score, e.get("shared_entities", [])
                        )
                        if verdict == "Not Related":
                            logger.info(f"LLM rejected connection: {art.title[:40]}...")
                            continue
                        elif verdict == "Weak":
                            e["connection_type"] = "Speculative"
                            e["llm_validation"] = "Weak"
                    except Exception as ex:
                        logger.warning(f"LLM validation failed, keeping connection: {ex}")
            validated_events.append(e)
        top_events = validated_events

        if not top_events:
            return self._no_meaningful_result(seed_article_id, seed, len(candidates))

        # 6. Analyze the event network for cross-domain patterns
        network_analysis = self._analyze_network(seed, top_events, articles, entity_map)

        # 6b. Strengthened weak-signal check — don't fabricate connections
        avg_rel = sum(e["relevance_score"] for e in top_events) / len(top_events)
        # Reject if: average score is low, OR all connections are just "Emerging Signal" (noise)
        all_emerging = all(e["connection_type"] == "Emerging Signal" for e in top_events)
        if avg_rel < 0.45 and (len(top_events) <= 2 or all_emerging):
            return self._no_meaningful_result(seed_article_id, seed, len(candidates))

        # 7. Generate narrative (LLM or fallback)
        narrative = await self._generate_narrative(
            seed, top_events, articles, network_analysis, preferred_language
        )

        # 8. Calculate overall confidence
        confidence = self._assess_confidence(top_events, network_analysis)

        # 9. Format response
        return {
            "seed_article": {
                "id": seed.id,
                "title": seed.title,
                "source": seed.source,
                "topic": getattr(seed, "topic", "general"),
                "published_at": str(seed.published_at),
            },
            "related_events": [
                {
                    "id": e["article_id"],
                    "title": articles[e["article_id"]].title if e["article_id"] in articles else "?",
                    "source": articles[e["article_id"]].source if e["article_id"] in articles else "?",
                    "topic": getattr(articles.get(e["article_id"]), "topic", "general"),
                    "published_at": str(articles[e["article_id"]].published_at) if e["article_id"] in articles else "",
                    "image_url": getattr(articles.get(e["article_id"]), "image_url", None),
                    "relevance_score": round(e["relevance_score"], 3),
                    "connection_type": e["connection_type"],
                    "shared_entities": e["shared_entities"][:5],
                    "domain_transition": e.get("domain_transition"),
                    "llm_validation": e.get("llm_validation", "Valid"),
                }
                for e in top_events
            ],
            "narrative": narrative,
            "confidence": confidence,
            "signals_summary": network_analysis,
            "total_candidates_scanned": len(candidates),
            "total_relevant": len(relevant),
        }

    # ── Candidate Retrieval ───────────────────────────────────────────────────

    async def _retrieve_candidates(
        self,
        seed: Article,
        seed_id: str,
        db: AsyncSession,
        max_candidates: int,
    ) -> Dict[str, float]:
        """
        Retrieve candidates via two channels:
          1. FAISS semantic similarity (broader search, top-K)
          2. Entity-linked articles (shares important entities)

        Returns dict of {article_id: faiss_similarity_score}
        """
        candidates: Dict[str, float] = {}

        # Channel 1: FAISS vector similarity (broad)
        seed_emb = self.embedding.get_embedding_by_id(seed_id)
        if seed_emb is not None:
            neighbours = await self.embedding.find_similar(seed_emb, k=max_candidates + 5)
            for aid, sim_score in neighbours:
                if aid != seed_id:
                    candidates[aid] = sim_score

        # Channel 2: Entity-linked articles
        # Find articles that share entities with the seed
        try:
            seed_entities_result = await db.execute(
                select(ArticleEntity.entity_id)
                .where(ArticleEntity.article_id == seed_id)
            )
            seed_entity_ids = [row[0] for row in seed_entities_result.fetchall()]

            if seed_entity_ids:
                # Find other articles with these entities
                linked_result = await db.execute(
                    select(ArticleEntity.article_id)
                    .where(
                        ArticleEntity.entity_id.in_(seed_entity_ids),
                        ArticleEntity.article_id != seed_id,
                    )
                )
                entity_linked = set(row[0] for row in linked_result.fetchall())

                # Add entity-linked articles that aren't already in FAISS results
                for aid in entity_linked:
                    if aid not in candidates:
                        candidates[aid] = 0.25  # Base score for entity-linked
                    else:
                        # Boost existing candidates that also share entities
                        candidates[aid] = min(1.0, candidates[aid] + 0.05)
        except Exception as e:
            logger.debug(f"Entity linking failed: {e}")

        # Channel 3: SQL topic + time window fallback (when FAISS empty + no entity links)
        if not candidates:
            try:
                from datetime import timedelta
                window = timedelta(days=7)
                q = (
                    select(Article.id)
                    .where(Article.id != seed_id)
                    .where(Article.published_at >= (seed.published_at - window))
                    .where(Article.published_at <= (seed.published_at + window))
                    .order_by(Article.published_at.desc())
                )
                if seed.topic and seed.topic != "general":
                    q = q.where(Article.topic == seed.topic)
                q = q.limit(max_candidates)
                sql_result = await db.execute(q)
                for row in sql_result.fetchall():
                    candidates[row[0]] = 0.45  # Moderate base score for topic+time matches
                logger.info(f"SQL fallback found {len(candidates)} candidates for explore")
            except Exception as e:
                logger.warning(f"SQL fallback for candidates failed: {e}")

        # Limit total candidates
        if len(candidates) > max_candidates:
            sorted_cands = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
            candidates = dict(sorted_cands[:max_candidates])

        return candidates

    # ── Batch Data Fetch ──────────────────────────────────────────────────────

    async def _batch_fetch(
        self,
        all_ids: List[str],
        seed: Article,
        db: AsyncSession,
    ) -> Tuple[Dict[str, Article], Dict[str, Set[str]], Dict[str, Optional[int]]]:
        """Single-pass batch fetch of articles, entities, and clusters."""
        # Articles
        batch = await db.execute(select(Article).where(Article.id.in_(all_ids)))
        articles = {a.id: a for a in batch.scalars().all()}
        if seed.id not in articles:
            articles[seed.id] = seed

        # Entities
        ent_result = await db.execute(
            select(ArticleEntity.article_id, Entity.text, Entity.type)
            .join(Entity, ArticleEntity.entity_id == Entity.id)
            .where(ArticleEntity.article_id.in_(list(articles.keys())))
        )
        entity_map: Dict[str, Set[str]] = defaultdict(set)
        for row in ent_result.fetchall():
            entity_map[row[0]].add(row[1])

        # Clusters
        cluster_result = await db.execute(
            select(ArticleCluster.article_id, ArticleCluster.cluster_id)
            .where(ArticleCluster.article_id.in_(list(articles.keys())))
        )
        cluster_map = {row[0]: row[1] for row in cluster_result.fetchall()}

        return articles, entity_map, cluster_map

    # ── Multi-Signal Scoring ──────────────────────────────────────────────────

    def _score_candidates(
        self,
        seed_id: str,
        seed: Article,
        candidate_ids: List[str],
        raw_candidates: Dict[str, float],
        articles: Dict[str, Article],
        entity_map: Dict[str, Set[str]],
        cluster_map: Dict[str, Optional[int]],
    ) -> List[Dict[str, Any]]:
        """
        Multi-signal scoring for each candidate against the seed.
        Signals: embedding similarity, entity overlap, temporal proximity,
                 source diversity, topic transition, cluster proximity.
        """
        seed_entities = entity_map.get(seed_id, set())
        seed_domain = _domain(getattr(seed, "topic", None))
        seed_cluster = cluster_map.get(seed_id)

        scored = []
        for cid in candidate_ids:
            if cid not in articles:
                continue

            candidate = articles[cid]
            cand_entities = entity_map.get(cid, set())
            cand_domain = _domain(getattr(candidate, "topic", None))
            cand_cluster = cluster_map.get(cid)

            # Signal 1: Embedding similarity (from FAISS, already computed)
            emb_sim = raw_candidates.get(cid, 0.0)
            # Normalize FAISS L2 distance to similarity if needed
            # Our embedding_service.find_similar returns cosine similarity
            emb_score = max(0.0, min(1.0, emb_sim))

            # Signal 2: Entity overlap (Overlap coefficient)
            shared = seed_entities & cand_entities
            if seed_entities and cand_entities:
                ent_overlap = len(shared) / min(len(seed_entities), len(cand_entities))
            else:
                ent_overlap = 0.0

            # Signal 3: Temporal proximity (exponential decay over 96h)
            try:
                diff_hours = abs((seed.published_at - candidate.published_at).total_seconds()) / 3600.0
                temp_score = math.exp(-diff_hours / 96.0)
            except Exception:
                temp_score = 0.5

            # Signal 4: Source diversity (different sources = more interesting)
            source_div = 1.0 if seed.source.lower() != candidate.source.lower() else 0.4

            # Signal 5: Topic transition analysis
            topic_score = 0.5  # neutral default
            domain_transition = None
            if seed_domain != "general" and cand_domain != "general":
                if seed_domain == cand_domain:
                    topic_score = 0.7  # same domain, related
                elif _is_pathway(seed_domain, cand_domain):
                    topic_score = 1.0  # known causal pathway!
                    domain_transition = f"{seed_domain} → {cand_domain}"
                else:
                    topic_score = 0.6  # cross-domain but no known pathway

            # Signal 6: Cluster proximity
            cluster_score = 0.5  # neutral
            if seed_cluster is not None and cand_cluster is not None:
                cluster_score = 1.0 if seed_cluster == cand_cluster else 0.3

            # Composite relevance score
            relevance = (
                0.30 * emb_score
                + 0.20 * ent_overlap
                + 0.15 * temp_score
                + 0.10 * source_div
                + 0.15 * topic_score
                + 0.10 * cluster_score
            )

            # Classify connection type
            if cluster_score == 1.0 and emb_score > 0.5:
                conn_type = "Same Story"
            elif domain_transition:
                conn_type = "Cross-Domain"
            elif ent_overlap > 0.5:
                conn_type = "Shared Actors"
            elif emb_score > 0.4 and temp_score > 0.7:
                conn_type = "Related Development"
            elif topic_score > 0.6:
                conn_type = "Thematic Link"
            else:
                conn_type = "Emerging Signal"

            scored.append({
                "article_id": cid,
                "relevance_score": round(relevance, 4),
                "connection_type": conn_type,
                "shared_entities": list(shared),
                "domain_transition": domain_transition,
                "signals": {
                    "embedding": round(emb_score, 3),
                    "entity_overlap": round(ent_overlap, 3),
                    "temporal": round(temp_score, 3),
                    "source_diversity": round(source_div, 3),
                    "topic_transition": round(topic_score, 3),
                    "cluster": round(cluster_score, 3),
                },
            })

        return scored

    # ── Network Analysis ──────────────────────────────────────────────────────

    def _analyze_network(
        self,
        seed: Article,
        top_events: List[Dict],
        articles: Dict[str, Article],
        entity_map: Dict[str, Set[str]],
    ) -> Dict[str, Any]:
        """Analyze the event network for patterns and cross-domain signals."""
        domains_seen = set()
        connection_types = defaultdict(int)
        all_shared_entities = set()
        domain_transitions = []

        seed_domain = _domain(getattr(seed, "topic", None))
        domains_seen.add(seed_domain)

        for event in top_events:
            aid = event["article_id"]
            ct = event["connection_type"]
            connection_types[ct] += 1

            if aid in articles:
                d = _domain(getattr(articles[aid], "topic", None))
                domains_seen.add(d)

            if event.get("domain_transition"):
                domain_transitions.append(event["domain_transition"])

            for ent in event["shared_entities"]:
                all_shared_entities.add(ent)

        # Determine dominant pattern
        if connection_types.get("Cross-Domain", 0) > 0:
            dominant_pattern = "Cross-Domain Impact Network"
        elif connection_types.get("Same Story", 0) > len(top_events) * 0.5:
            dominant_pattern = "Multi-Source Coverage"
        elif connection_types.get("Shared Actors", 0) > len(top_events) * 0.3:
            dominant_pattern = "Actor-Linked Events"
        elif connection_types.get("Related Development", 0) > len(top_events) * 0.3:
            dominant_pattern = "Evolving Story"
        else:
            dominant_pattern = "Emerging Pattern"

        return {
            "total_events": len(top_events) + 1,  # +1 for seed
            "domains_covered": list(d for d in domains_seen if d != "general"),
            "connection_breakdown": dict(connection_types),
            "domain_transitions": domain_transitions[:5],
            "key_entities": list(all_shared_entities)[:10],
            "dominant_pattern": dominant_pattern,
        }

    # ── Confidence Assessment ─────────────────────────────────────────────────

    def _assess_confidence(
        self,
        top_events: List[Dict],
        network_analysis: Dict,
    ) -> Dict[str, Any]:
        """Assess overall confidence in the event network."""
        if not top_events:
            return {"level": "Insufficient Data", "score": 0.0}

        avg_relevance = sum(e["relevance_score"] for e in top_events) / len(top_events)
        max_relevance = max(e["relevance_score"] for e in top_events)
        n_cross_domain = sum(
            1 for e in top_events if e["connection_type"] == "Cross-Domain"
        )
        n_shared_actors = sum(
            1 for e in top_events if len(e["shared_entities"]) > 0
        )

        # Composite confidence
        conf_score = (
            0.40 * avg_relevance
            + 0.25 * max_relevance
            + 0.15 * min(1.0, n_shared_actors / max(len(top_events), 1))
            + 0.20 * min(1.0, len(top_events) / 5)
        )

        if conf_score >= 0.60:
            level = "Strong"
            description = "Multiple strong signals support these connections. High-confidence analytical assessment."
        elif conf_score >= 0.45:
            level = "Moderate"
            description = "Several meaningful signals detected. Connections are plausible but not definitive."
        elif conf_score >= 0.35:
            level = "Weak"
            description = "Limited signals detected. These connections are tentative and should be treated with caution."
        else:
            level = "Insufficient Evidence"
            description = "Very weak or no meaningful signals. No reliable relationship can be established from available data."

        return {
            "level": level,
            "score": round(conf_score, 3),
            "description": description,
            "metrics": {
                "avg_relevance": round(avg_relevance, 3),
                "max_relevance": round(max_relevance, 3),
                "cross_domain_links": n_cross_domain,
                "entity_linked_events": n_shared_actors,
            },
        }

    # ── Narrative Generation ──────────────────────────────────────────────────

    async def _generate_narrative(
        self,
        seed: Article,
        top_events: List[Dict],
        articles: Dict[str, Article],
        network_analysis: Dict,
        preferred_language: str,
    ) -> str:
        """Generate structured narrative via LLM or fallback."""

        # Format related events for prompt
        related_parts = []
        for i, event in enumerate(top_events[:8], 1):
            aid = event["article_id"]
            art = articles.get(aid)
            if not art:
                continue
            content_preview = _sanitize_content(art.content)[:400] if art.content else ""
            shared = ", ".join(event["shared_entities"][:4]) or "thematic overlap"
            related_parts.append(
                f"Event {i}: [{art.source}] \"{art.title}\"\n"
                f"  Published: {art.published_at}\n"
                f"  Topic: {getattr(art, 'topic', 'general')}\n"
                f"  Connection: {event['connection_type']} (score: {event['relevance_score']:.2f})\n"
                f"  Shared signals: {shared}\n"
                f"  Content: {content_preview}"
            )

        # Format signals summary
        domains = network_analysis.get("domains_covered", [])
        transitions = network_analysis.get("domain_transitions", [])
        key_entities = network_analysis.get("key_entities", [])

        signals_parts = [
            f"Pattern type: {network_analysis.get('dominant_pattern', 'Unknown')}",
            f"Domains covered: {', '.join(domains) if domains else 'single domain'}",
        ]
        if transitions:
            signals_parts.append(f"Domain transitions detected: {', '.join(transitions)}")
        if key_entities:
            signals_parts.append(f"Key shared entities across events: {', '.join(key_entities[:8])}")

        # Try LLM generation
        prompt = EVENT_NETWORK_PROMPT.format(
            n_related=len(top_events),
            seed_title=seed.title,
            seed_source=seed.source,
            seed_published=str(seed.published_at),
            seed_content=_sanitize_content(seed.content)[:1200] if seed.content else "",
            related_events_text="\n\n".join(related_parts),
            signals_summary="\n".join(signals_parts),
            output_language=preferred_language,
        )

        try:
            # Use Haiku for narrative generation (explains signals found by scoring engine)
            if hasattr(self.llm, '_invoke_fast'):
                result = await self.llm._invoke_fast(prompt)
                if result:
                    return result
            # Try generate_deep_analysis as fallback LLM path
            elif hasattr(self.llm, 'generate_deep_analysis'):
                result = await self.llm.generate_deep_analysis(
                    {"title": seed.title, "content": seed.content, "source": seed.source,
                     "published_at": str(seed.published_at)},
                    [], None, preferred_language
                )
                if result:
                    return result
        except Exception as e:
            logger.error(f"LLM narrative generation failed: {e}")

        # Fallback: rule-based narrative
        return self._fallback_narrative(seed, top_events, articles, network_analysis)

    def _fallback_narrative(
        self,
        seed: Article,
        top_events: List[Dict],
        articles: Dict[str, Article],
        network_analysis: Dict,
    ) -> str:
        """Rule-based narrative when LLM is unavailable."""
        parts = []
        pattern = network_analysis.get("dominant_pattern", "Event Network")
        domains = network_analysis.get("domains_covered", [])
        transitions = network_analysis.get("domain_transitions", [])
        key_entities = network_analysis.get("key_entities", [])

        # Event Network Overview
        n = len(top_events)
        parts.append(f"**Event Network Overview**\n")
        parts.append(
            f"Analysis of \"{seed.title}\" identified {n} potentially related events "
            f"forming a **{pattern}**. "
        )
        if domains:
            parts.append(
                f"These events span across {', '.join(domains)} domains, "
                f"suggesting interconnections that go beyond a single news story."
            )
        else:
            parts.append(
                "Multiple sources are covering aspects of this developing situation."
            )

        # How These Events Connect
        parts.append(f"\n\n**How These Events Connect**\n")
        for i, event in enumerate(top_events[:5]):
            aid = event["article_id"]
            art = articles.get(aid)
            if not art:
                continue
            shared_text = ", ".join(event["shared_entities"][:3]) if event["shared_entities"] else "thematic similarity"
            conn = event["connection_type"]
            score_pct = int(event["relevance_score"] * 100)

            if conn == "Same Story":
                parts.append(
                    f"• **[{art.source}]** \"{art.title[:70]}\" — "
                    f"Part of the same developing story ({score_pct}% match). "
                    f"Shared references: {shared_text}."
                )
            elif conn == "Cross-Domain":
                parts.append(
                    f"• **[{art.source}]** \"{art.title[:70]}\" — "
                    f"**Cross-domain connection** ({event.get('domain_transition', '')}). "
                    f"This suggests cascading effects from one sector to another."
                )
            elif conn == "Shared Actors":
                parts.append(
                    f"• **[{art.source}]** \"{art.title[:70]}\" — "
                    f"Involves the same actors: {shared_text}. "
                    f"Actions in one context may have consequences in the other."
                )
            else:
                parts.append(
                    f"• **[{art.source}]** \"{art.title[:70]}\" — "
                    f"{conn} ({score_pct}% relevance)."
                )

        # Cross-Domain Impacts
        if transitions:
            parts.append(f"\n\n**Cross-Domain Impacts**\n")
            parts.append(
                f"This event network reveals potential ripple effects across domains: "
                f"{', '.join(transitions)}. "
                f"Events in one sphere may be driving or responding to developments in another."
            )

        # Emerging Patterns
        if key_entities:
            parts.append(f"\n\n**Emerging Patterns**\n")
            parts.append(
                f"Key actors and entities appearing across multiple events: "
                f"**{', '.join(key_entities[:6])}**. "
                f"The convergence of these references across {n} events suggests an evolving situation "
                f"that may develop further in the coming days."
            )

        # What to Watch
        parts.append(f"\n\n**What To Watch**\n")
        parts.append(
            f"Monitor official responses and policy changes related to this event cluster. "
            f"Cross-domain effects often take 24-72 hours to materialize in public reporting."
        )

        parts.append(
            f"\n\n*This analysis is based on automated signal detection across {n} events. "
            f"Connections represent analytical possibilities, not confirmed causal relationships.*"
        )

        return "\n".join(parts)

    def _empty_result(self, seed_id: str, seed: Article) -> Dict[str, Any]:
        """Return empty result when no connections found."""
        return {
            "seed_article": {
                "id": seed.id,
                "title": seed.title,
                "source": seed.source,
                "topic": getattr(seed, "topic", "general"),
                "published_at": str(seed.published_at),
            },
            "related_events": [],
            "narrative": "No significant connections found for this article in the current corpus.",
            "confidence": {"level": "Insufficient Data", "score": 0.0, "description": "Not enough related events found."},
            "signals_summary": {"total_events": 1, "domains_covered": [], "connection_breakdown": {}},
            "total_candidates_scanned": 0,
            "total_relevant": 0,
        }

    def _no_meaningful_result(self, seed_id: str, seed: Article, candidates_scanned: int) -> Dict[str, Any]:
        """Return result when signals exist but are too weak for a meaningful relationship."""
        return {
            "seed_article": {
                "id": seed.id,
                "title": seed.title,
                "source": seed.source,
                "topic": getattr(seed, "topic", "general"),
                "published_at": str(seed.published_at),
            },
            "related_events": [],
            "narrative": (
                "No meaningful relationship was detected between this article and other events "
                "in the current corpus. While some articles share surface-level similarities, "
                "the connection signals (entity overlap, temporal proximity, topic transitions) "
                "are too weak to support a reliable analytical assessment. "
                "This does not mean no relationship exists — it means the available evidence "
                "is insufficient to draw meaningful conclusions at this time."
            ),
            "confidence": {
                "level": "No Significant Relationship",
                "score": 0.0,
                "description": "Signals are too weak to establish a meaningful connection between these events.",
            },
            "signals_summary": {"total_events": 1, "domains_covered": [], "connection_breakdown": {}},
            "total_candidates_scanned": candidates_scanned,
            "total_relevant": 0,
        }
