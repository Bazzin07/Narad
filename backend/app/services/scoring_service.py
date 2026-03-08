"""
Scoring Service — deterministic weighted relation scoring.
No LLM calls. Combines multiple signals into a single score.

Formula:
  score = 0.40 * embedding_similarity
        + 0.25 * entity_overlap
        + 0.15 * temporal_proximity
        + 0.10 * source_diversity
        + 0.10 * graph_distance
"""
import math
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Set, Optional

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding_service import EmbeddingService
from app.services.entity_service import EntityService
from app.services.clustering_service import ClusteringService

logger = logging.getLogger(__name__)


# ── Weights ───────────────────────────────────────────────────────────────────

W_EMBEDDING = 0.40
W_ENTITY = 0.25
W_TEMPORAL = 0.15
W_SOURCE = 0.10
W_GRAPH = 0.10


# ── Data Classes ──────────────────────────────────────────────────────────────


@dataclass
class RelationScore:
    total_score: float
    confidence: str  # "Strong", "Moderate", "Weak", "Not Related"
    embedding_similarity: float
    entity_overlap: float
    temporal_proximity: float
    source_diversity: float
    graph_distance: float
    credibility_factor: float = 1.0  # avg credibility of both articles

    def to_dict(self) -> dict:
        return asdict(self)


def classify_confidence(score: float) -> str:
    """Classify score into confidence levels."""
    if score >= 0.75:
        return "Strong"
    elif score >= 0.55:
        return "Moderate"
    elif score >= 0.40:
        return "Weak"
    else:
        return "Not Related"


# ── Scoring Service ───────────────────────────────────────────────────────────


class ScoringService:
    """Calculates deterministic relation scores with weighted components."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        entity_service: EntityService,
        clustering_service: ClusteringService,
    ):
        self.embedding_service = embedding_service
        self.entity_service = entity_service
        self.clustering_service = clustering_service

    async def calculate_relation_score(
        self,
        article1_id: str,
        article2_id: str,
        db: AsyncSession,
        article1=None,
        article2=None,
    ) -> RelationScore:
        """
        Calculate the weighted relation score between two articles.
        Each component returns a value in [0, 1].
        """
        # 1. Embedding similarity
        emb_sim = self._embedding_similarity(article1_id, article2_id)

        # 2. Entity overlap — cross-lingual fuzzy matching
        ent_overlap = await self.entity_service.get_shared_entity_count(
            article1_id, article2_id, db
        )

        # 3. Temporal proximity
        t1 = article1.published_at if article1 else datetime.utcnow()
        t2 = article2.published_at if article2 else datetime.utcnow()
        temp_score = self._temporal_proximity(t1, t2)

        # 4. Source diversity
        src1 = article1.source if article1 else ""
        src2 = article2.source if article2 else ""
        src_div = self._source_diversity(src1, src2)

        # 5. Graph distance (cluster-based)
        c1 = await self.clustering_service.get_article_cluster(article1_id, db)
        c2 = await self.clustering_service.get_article_cluster(article2_id, db)
        graph_dist = self._graph_distance(c1, c2)

        # Weighted combination (formula UNCHANGED)
        raw_score = (
            W_EMBEDDING * emb_sim
            + W_ENTITY * ent_overlap
            + W_TEMPORAL * temp_score
            + W_SOURCE * src_div
            + W_GRAPH * graph_dist
        )

        raw_score = max(0.0, min(1.0, raw_score))

        # Apply credibility multiplier (Phase D)
        cred1 = getattr(article1, 'credibility_weight', 1.0) or 1.0
        cred2 = getattr(article2, 'credibility_weight', 1.0) or 1.0
        avg_cred = (cred1 + cred2) / 2.0
        final_score = max(0.0, min(1.0, raw_score * avg_cred))

        score = RelationScore(
            total_score=round(final_score, 4),
            confidence=classify_confidence(final_score),
            embedding_similarity=round(emb_sim, 4),
            entity_overlap=round(ent_overlap, 4),
            temporal_proximity=round(temp_score, 4),
            source_diversity=round(src_div, 4),
            graph_distance=round(graph_dist, 4),
            credibility_factor=round(avg_cred, 4),
        )

        logger.info(
            f"Score({article1_id[:8]}..↔{article2_id[:8]}..): "
            f"{score.total_score} ({score.confidence}) [cred={avg_cred:.2f}]"
        )
        return score

    # ── Component Calculations ────────────────────────────────────────────────

    def _embedding_similarity(self, article1_id: str, article2_id: str) -> float:
        """Cosine similarity between article embeddings. Returns [0, 1]."""
        emb1 = self.embedding_service.get_embedding_by_id(article1_id)
        emb2 = self.embedding_service.get_embedding_by_id(article2_id)

        if emb1 is None or emb2 is None:
            return 0.0

        sim = self.embedding_service.cosine_similarity(emb1, emb2)
        # Cosine similarity is in [-1, 1] — clamp to [0, 1]
        return max(0.0, min(1.0, sim))

    def _entity_overlap(self, entities1: Set[str], entities2: Set[str]) -> float:
        """
        Overlap coefficient of entity sets. Returns [0, 1].
        Uses |intersection| / min(|set1|, |set2|) instead of Jaccard.
        This avoids penalizing when one article has more entities than the other.
        If all entities of the smaller set appear in the larger set → 1.0.
        """
        if not entities1 and not entities2:
            return 0.0
        if not entities1 or not entities2:
            return 0.0
        intersection = entities1 & entities2
        min_size = min(len(entities1), len(entities2))
        return len(intersection) / min_size

    def _temporal_proximity(self, time1: datetime, time2: datetime) -> float:
        """
        Score based on time difference using exponential decay.
        Returns [0, 1]. Same-day articles score ~1.0, 7+ days apart score ~0.
        """
        diff_hours = abs((time1 - time2).total_seconds()) / 3600.0
        # Decay: score = exp(-diff_hours / 72)
        # 72h (3 days) → 0.37, 168h (7 days) → 0.10
        return math.exp(-diff_hours / 72.0)

    def _source_diversity(self, source1: str, source2: str) -> float:
        """
        Score based on source diversity.
        Different sources → 1.0 (cross-source coverage is a strong signal).
        Same source → 0.5 (neutral — same source covering same event is normal).
        """
        if not source1 or not source2:
            return 0.5
        return 1.0 if source1.lower() != source2.lower() else 0.5

    def _graph_distance(self, cluster1: Optional[int], cluster2: Optional[int]) -> float:
        """
        Score based on cluster membership.
        Same cluster → 1.0, different clusters → 0.2, unclustered → 0.5.
        """
        if cluster1 is None or cluster2 is None:
            return 0.5  # can't determine — neutral score
        if cluster1 == cluster2:
            return 1.0  # same event cluster
        return 0.2  # different clusters
