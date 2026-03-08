"""
Causal Chain Detection Service — Micro-Signal Intelligence.

Upgraded from v1 pure-similarity chains to v2 multi-signal chains:
  - Lower threshold (0.30) for exploratory graph
  - Signal amplification for rare entities and cross-domain links
  - Chain labeling: Direct Similarity, Indirect Ripple, Cross-Domain Impact, Emerging Pattern
  - Narrative framing: "Potential emerging link" — never claims causality

Chain score = min(link_scores) * chain_decay^hops * signal_amplification
"""
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
# v2: lowered from 0.35 → 0.30 for exploratory graph
MIN_LINK_SCORE = 0.30
CHAIN_DECAY = 0.85
MAX_HOPS = 3
MIN_CHAIN_SCORE = 0.20  # lowered from 0.25 for emerging patterns

# ── Topic domain groupings ───────────────────────────────────────────────────
DOMAIN_GROUPS = {
    "military": "security",
    "terrorism": "security",
    "diplomacy": "geopolitics",
    "politics": "geopolitics",
    "economy": "economics",
    "energy": "economics",
    "business": "economics",
    "agriculture": "economics",
    "technology": "technology",
    "health": "social",
    "education": "social",
    "environment": "environment",
    "sports": "sports",
    "general": "general",
}

# ── Cross-Domain Transition Matrix ────────────────────────────────────────────
# Known causal pathways: if a link crosses these domains, it's more likely
# to represent a real indirect causal chain rather than coincidence.
# Pairs are bidirectional.
CAUSAL_TRANSITIONS = {
    ("security", "geopolitics"),
    ("security", "economics"),
    ("geopolitics", "economics"),
    ("economics", "social"),
    ("economics", "environment"),
    ("geopolitics", "social"),
    ("technology", "economics"),
    ("technology", "security"),
    ("environment", "economics"),
    ("environment", "social"),
}


def _is_causal_transition(domain_a: str, domain_b: str) -> bool:
    """Check if two domains have a known causal transition pathway."""
    pair = tuple(sorted([domain_a, domain_b]))
    return pair in CAUSAL_TRANSITIONS or (pair[1], pair[0]) in CAUSAL_TRANSITIONS


def _get_domain(topic: Optional[str]) -> str:
    """Map topic to broad domain group."""
    if not topic:
        return "general"
    return DOMAIN_GROUPS.get(topic.lower(), "general")


def _classify_chain_type(
    path_topics: List[str],
    path_scores: List[float],
    shared_entity_counts: List[int],
) -> str:
    """
    Classify a chain into one of four types:
      - Direct Similarity: all links strong (>0.50), same domain
      - Indirect Ripple: moderate links, some shared entities
      - Cross-Domain Impact: links span different domain groups
      - Emerging Pattern: weak but consistent multi-hop pattern
    """
    domains = [_get_domain(t) for t in path_topics]
    unique_domains = set(d for d in domains if d != "general")
    avg_score = sum(path_scores) / len(path_scores) if path_scores else 0
    min_score = min(path_scores) if path_scores else 0

    # Cross-domain if 2+ distinct non-general domains
    if len(unique_domains) >= 2:
        return "Cross-Domain Impact"

    # Direct similarity if all links strong
    if min_score >= 0.50:
        return "Direct Similarity"

    # Emerging pattern if weak but multi-hop
    if min_score < 0.40 and len(path_scores) >= 2:
        return "Emerging Pattern"

    # Default: indirect ripple
    return "Indirect Ripple"


class CausalChainService:
    """Detects multi-hop causal chains with micro-signal intelligence."""

    def __init__(self, scoring_service, entity_service, embedding_service):
        self.scoring = scoring_service
        self.entity = entity_service
        self.embedding = embedding_service

    async def detect_chains(
        self,
        seed_article_id: str,
        db: AsyncSession,
        max_hops: int = MAX_HOPS,
        top_k_neighbours: int = 10,
    ) -> Dict[str, Any]:
        """
        Starting from a seed article, discover multi-hop causal chains.

        v3: Batch DB queries to eliminate N+1 bottleneck.
        """
        # 1. Get seed article
        result = await db.execute(select(Article).where(Article.id == seed_article_id))
        seed = result.scalar_one_or_none()
        if not seed:
            raise ValueError(f"Article {seed_article_id} not found")

        # 2. Find FAISS neighbours (broader search)
        seed_emb = self.embedding.get_embedding_by_id(seed_article_id)
        if seed_emb is None:
            raise ValueError("Seed article has no embedding")

        neighbours = await self.embedding.find_similar(seed_emb, k=top_k_neighbours + 1)
        neighbour_ids = [aid for aid, _ in neighbours if aid != seed_article_id][:top_k_neighbours]

        if not neighbour_ids:
            return {"seed": seed_article_id, "chains": [], "graph_nodes": 0}

        # 3. BATCH fetch all neighbour articles (single query instead of N+1)
        all_needed_ids = [seed_article_id] + neighbour_ids
        batch_result = await db.execute(
            select(Article).where(Article.id.in_(all_needed_ids))
        )
        articles = {a.id: a for a in batch_result.scalars().all()}
        if seed_article_id not in articles:
            articles[seed_article_id] = seed

        # 4. BATCH fetch all cluster assignments (single query)
        from app.models.article import ArticleCluster
        cluster_result = await db.execute(
            select(ArticleCluster.article_id, ArticleCluster.cluster_id)
            .where(ArticleCluster.article_id.in_(list(articles.keys())))
        )
        cluster_map = {}
        for row in cluster_result.fetchall():
            cluster_map[row[0]] = row[1]

        # 5. BATCH fetch all entity associations (single query)
        from app.models.article import Entity, ArticleEntity
        entity_result = await db.execute(
            select(ArticleEntity.article_id, Entity.text, Entity.type)
            .join(Entity, ArticleEntity.entity_id == Entity.id)
            .where(ArticleEntity.article_id.in_(list(articles.keys())))
        )
        entity_map: Dict[str, Set[str]] = defaultdict(set)
        for row in entity_result.fetchall():
            entity_map[row[0]].add(row[1])

        # 6. Build adjacency graph with pairwise scores (no more DB calls)
        all_ids = list(articles.keys())
        graph: Dict[str, Dict[str, float]] = defaultdict(dict)
        edge_details: Dict[Tuple[str, str], Dict] = {}
        entity_frequency: Dict[str, int] = defaultdict(int)

        for i, id_a in enumerate(all_ids):
            for id_b in all_ids[i + 1:]:
                if id_a not in articles or id_b not in articles:
                    continue
                try:
                    # Compute embedding similarity (in-memory, no DB)
                    emb_sim = self.scoring._embedding_similarity(id_a, id_b)

                    # Compute shared entities from pre-fetched data (in-memory)
                    shared_texts = list(entity_map.get(id_a, set()) & entity_map.get(id_b, set()))
                    ent_overlap = min(1.0, len(shared_texts) / 3.0) if shared_texts else 0.0

                    # Temporal proximity (in-memory)
                    a1, a2 = articles[id_a], articles[id_b]
                    temp_score = self.scoring._temporal_proximity(a1.published_at, a2.published_at)
                    src_div = self.scoring._source_diversity(a1.source, a2.source)

                    # Graph distance from pre-fetched clusters (in-memory)
                    c1 = cluster_map.get(id_a)
                    c2 = cluster_map.get(id_b)
                    graph_dist = self.scoring._graph_distance(c1, c2)

                    # Credibility
                    cred1 = getattr(a1, 'credibility_weight', 1.0) or 1.0
                    cred2 = getattr(a2, 'credibility_weight', 1.0) or 1.0
                    avg_cred = (cred1 + cred2) / 2.0

                    # Weighted combination (same formula as ScoringService)
                    raw_score = (
                        0.35 * emb_sim
                        + 0.25 * ent_overlap
                        + 0.15 * temp_score
                        + 0.10 * src_div
                        + 0.15 * graph_dist
                    )
                    raw_score = max(0.0, min(1.0, raw_score * avg_cred))

                    # Track entity frequency for rarity boost
                    for text in shared_texts:
                        entity_frequency[text] += 1

                    # Signal amplification
                    amplified_score = self._amplify_signal(
                        raw_score, a1, a2, shared_texts, entity_frequency,
                    )

                    if amplified_score >= MIN_LINK_SCORE:
                        graph[id_a][id_b] = amplified_score
                        graph[id_b][id_a] = amplified_score

                        from app.models.schemas import RelationScore
                        confidence = "strong" if amplified_score >= 0.7 else "moderate" if amplified_score >= 0.5 else "weak"
                        edge_details[(id_a, id_b)] = {
                            "score": amplified_score,
                            "raw_score": raw_score,
                            "confidence": confidence,
                            "shared_entities": shared_texts,
                        }
                        edge_details[(id_b, id_a)] = edge_details[(id_a, id_b)]
                except Exception as e:
                    logger.debug(f"Score failed for {id_a[:8]}↔{id_b[:8]}: {e}")

        # 7. BFS from seed to find all paths up to max_hops
        chains = self._find_chains(seed_article_id, graph, max_hops)

        # 8. Score, classify, and format chains
        ranked_chains = []
        for path in chains:
            chain_info = self._score_chain(path, graph, edge_details, articles)
            if chain_info["chain_score"] >= MIN_CHAIN_SCORE:
                ranked_chains.append(chain_info)

        ranked_chains.sort(key=lambda c: c["chain_score"], reverse=True)

        return {
            "seed": {
                "id": seed_article_id,
                "title": seed.title,
                "source": seed.source,
            },
            "chains": ranked_chains[:10],
            "graph_nodes": len(articles),
            "graph_edges": sum(len(v) for v in graph.values()) // 2,
        }

    def _amplify_signal(
        self,
        base_score: float,
        article_a: Article,
        article_b: Article,
        shared_entities: List[str],
        entity_frequency: Dict[str, int],
    ) -> float:
        """
        v3 signal amplification:
        - Rare entity boost: stronger boost for unique shared entities
        - Cross-domain boost: links across causal transition paths get higher uplift
        - Penalize same-source, same-topic (likely same story)
        """
        amplification = 1.0

        # Rare entity boost (entities appearing in ≤2 edges get 8% boost each, max 20%)
        rare_boost = 0.0
        for ent in shared_entities:
            if entity_frequency.get(ent, 0) <= 2:
                rare_boost += 0.08
        rare_boost = min(rare_boost, 0.20)
        amplification += rare_boost

        # Cross-domain boost
        domain_a = _get_domain(getattr(article_a, 'topic', None))
        domain_b = _get_domain(getattr(article_b, 'topic', None))
        if domain_a != "general" and domain_b != "general" and domain_a != domain_b:
            if _is_causal_transition(domain_a, domain_b):
                amplification += 0.15  # Known causal pathway → strong boost
            else:
                amplification += 0.08  # Unknown cross-domain → moderate boost

        # Slight penalty for same-source + same-topic (likely same story duplicate)
        if (article_a.source == article_b.source and
            getattr(article_a, 'topic', None) == getattr(article_b, 'topic', None)):
            amplification *= 0.92

        return min(1.0, base_score * amplification)

    def _find_chains(
        self,
        seed_id: str,
        graph: Dict[str, Dict[str, float]],
        max_hops: int,
    ) -> List[List[str]]:
        """BFS to find all paths from seed, up to max_hops."""
        chains = []
        queue = [(seed_id, [seed_id])]

        while queue:
            current, path = queue.pop(0)

            if len(path) > 1:
                chains.append(path[:])

            if len(path) - 1 >= max_hops:
                continue

            for neighbour, score in graph.get(current, {}).items():
                if neighbour not in path:
                    queue.append((neighbour, path + [neighbour]))

        # Only return multi-hop chains (length >= 3 = at least 2 hops)
        return [c for c in chains if len(c) >= 3]

    def _score_chain(
        self,
        path: List[str],
        graph: Dict[str, Dict[str, float]],
        edge_details: Dict,
        articles: Dict[str, Article],
    ) -> Dict[str, Any]:
        """Score a chain: weakest link * decay^(num_hops). Classify chain type."""
        hops = len(path) - 1
        link_scores = []
        links = []
        shared_entity_counts = []
        path_topics = []

        for node_id in path:
            art = articles.get(node_id)
            if art:
                path_topics.append(getattr(art, 'topic', 'general') or 'general')

        for i in range(hops):
            a_id, b_id = path[i], path[i + 1]
            score = graph.get(a_id, {}).get(b_id, 0)
            link_scores.append(score)

            detail = edge_details.get((a_id, b_id), {})
            shared = detail.get("shared_entities", [])
            shared_entity_counts.append(len(shared))

            links.append({
                "from": {
                    "id": a_id,
                    "title": articles[a_id].title if a_id in articles else "?",
                    "source": articles[a_id].source if a_id in articles else "?",
                },
                "to": {
                    "id": b_id,
                    "title": articles[b_id].title if b_id in articles else "?",
                    "source": articles[b_id].source if b_id in articles else "?",
                },
                "score": detail.get("score", score),
                "raw_score": detail.get("raw_score", score),
                "confidence": detail.get("confidence", "Unknown"),
                "shared_entities": shared,
            })

        # Chain score = weakest link * decay^hops
        chain_score = min(link_scores) * (CHAIN_DECAY ** hops) if link_scores else 0

        # Classify chain type
        chain_type = _classify_chain_type(path_topics, link_scores, shared_entity_counts)

        # Cross-domain chain bonus: chains that traverse known causal pathways
        # get a 20% score boost to surface indirect cause-and-effect
        if chain_type == "Cross-Domain Impact":
            domains_in_path = [_get_domain(t) for t in path_topics if _get_domain(t) != "general"]
            has_causal_path = False
            for i in range(len(domains_in_path) - 1):
                if _is_causal_transition(domains_in_path[i], domains_in_path[i + 1]):
                    has_causal_path = True
                    break
            if has_causal_path:
                chain_score = min(1.0, chain_score * 1.20)

        # Build path nodes
        chain_nodes = []
        for node_id in path:
            art = articles.get(node_id)
            if art:
                chain_nodes.append({
                    "id": node_id,
                    "title": art.title,
                    "source": art.source,
                    "language": art.language,
                    "published_at": str(art.published_at),
                    "topic": getattr(art, 'topic', 'general'),
                })

        return {
            "chain_score": round(chain_score, 4),
            "hops": hops,
            "weakest_link": round(min(link_scores), 4) if link_scores else 0,
            "chain_type": chain_type,
            "path": chain_nodes,
            "links": links,
            "narrative": self._generate_narrative(chain_nodes, links, chain_type),
        }

    def _generate_narrative(self, nodes: list, links: list, chain_type: str) -> str:
        """Generate a hedged, non-deterministic narrative for the chain."""
        if len(nodes) < 2:
            return ""

        # v2: hedged language — never claims causality
        type_label = chain_type.upper()
        parts = [f"**{type_label} — Potential Signal Chain ({len(nodes)} events, {len(links)} links):**\n"]

        # Add hedge disclaimer based on chain type
        if chain_type == "Emerging Pattern":
            parts.append("_⚠ Weak but consistent pattern. Monitor for development._\n")
        elif chain_type == "Cross-Domain Impact":
            parts.append("_ℹ Cross-domain signals detected. Possible indirect connection._\n")
        elif chain_type == "Indirect Ripple":
            parts.append("_ℹ Potential ripple effect based on shared signals._\n")

        for i, node in enumerate(nodes):
            topic_tag = f" [{node.get('topic', '')}]" if node.get('topic') and node.get('topic') != 'general' else ""
            if i == 0:
                parts.append(f"1. 🔵 **Origin:** [{node['source']}]{topic_tag} *\"{node['title'][:60]}\"*")
            elif i == len(nodes) - 1:
                parts.append(f"{i+1}. 🔴 **Signal End:** [{node['source']}]{topic_tag} *\"{node['title'][:60]}\"*")
            else:
                parts.append(f"{i+1}. 🟡 **Via:** [{node['source']}]{topic_tag} *\"{node['title'][:60]}\"*")

            if i < len(links):
                link = links[i]
                shared = ", ".join(link["shared_entities"][:3]) if link["shared_entities"] else "thematic"
                parts.append(f"   ↓ ({link['score']:.2f}) — shared signals: {shared}")

        parts.append(f"\n_Potential emerging link based on shared signals. Not a confirmed causal relationship._")

        return "\n".join(parts)


async def detect_chains_for_cluster(
    cluster_article_ids: List[str],
    scoring_service,
    entity_service,
    db: AsyncSession,
) -> List[Dict]:
    """
    Given articles in a cluster, find all significant causal chains.
    Useful for building the cluster narrative.
    """
    graph: Dict[str, Dict[str, float]] = defaultdict(dict)

    for i, id_a in enumerate(cluster_article_ids):
        for id_b in cluster_article_ids[i + 1:]:
            try:
                score = await scoring_service.calculate_relation_score(id_a, id_b, db)
                if score.total_score >= MIN_LINK_SCORE:
                    graph[id_a][id_b] = score.total_score
                    graph[id_b][id_a] = score.total_score
            except Exception:
                pass

    all_chains = []
    chain_service = CausalChainService.__new__(CausalChainService)
    for seed_id in cluster_article_ids:
        paths = chain_service._find_chains(seed_id, graph, MAX_HOPS)
        for path in paths:
            all_chains.append((frozenset(path), path))

    seen = set()
    unique_chains = []
    for key, path in all_chains:
        if key not in seen:
            seen.add(key)
            unique_chains.append(path)

    return unique_chains
