"""
Clustering Service — groups articles into event clusters using DBSCAN.
Deterministic. No LLM calls.
"""
import logging
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, Cluster, ArticleCluster
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class ClusteringService:
    """Groups related articles into event clusters using DBSCAN on embeddings."""

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service

    async def cluster_articles(self, db: AsyncSession) -> Dict[int, List[str]]:
        """
        Run DBSCAN clustering on all embedded articles.
        Returns {cluster_label: [article_ids]}.
        """
        from sklearn.cluster import DBSCAN

        es = self.embedding_service
        es._ensure_faiss_index()

        if es._faiss_index is None or es._faiss_index.ntotal < 2:
            logger.info("Not enough articles for clustering")
            return {}

        # Get all embeddings from FAISS
        import faiss
        n = es._faiss_index.ntotal
        dim = es.dim
        xb = faiss.rev_swig_ptr(es._faiss_index.get_xb(), n * dim)
        embeddings = xb.reshape(n, dim).copy()

        # DBSCAN with cosine distance
        # eps=0.4 means articles need to be within 0.4 distance (= 0.6 similarity) to cluster
        clustering = DBSCAN(eps=0.4, min_samples=2, metric="cosine")
        labels = clustering.fit_predict(embeddings)

        # Group by cluster label
        clusters: Dict[int, List[str]] = {}
        for idx, label in enumerate(labels):
            if label == -1:
                continue  # noise point — unclustered
            label = int(label)
            if label not in clusters:
                clusters[label] = []
            if idx < len(es._faiss_article_ids):
                clusters[label].append(es._faiss_article_ids[idx])

        # Store cluster assignments in DB
        await self._store_clusters(clusters, db)

        logger.info(f"Clustering: found {len(clusters)} clusters from {n} articles")
        return clusters

    async def _store_clusters(self, clusters: Dict[int, List[str]], db: AsyncSession) -> None:
        """Store cluster assignments in the database."""
        # Clear existing clusters
        await db.execute(delete(ArticleCluster))
        await db.execute(delete(Cluster))
        await db.flush()

        for label, article_ids in clusters.items():
            cluster = Cluster(label=f"event_cluster_{label}")
            db.add(cluster)
            await db.flush()

            for article_id in article_ids:
                assoc = ArticleCluster(article_id=article_id, cluster_id=cluster.id)
                db.add(assoc)

            # Mark articles as clustered
            for article_id in article_ids:
                result = await db.execute(select(Article).where(Article.id == article_id))
                article = result.scalar_one_or_none()
                if article:
                    article.processed = max(article.processed, 3)

        await db.commit()

    async def get_cluster_members(self, cluster_id: int, db: AsyncSession) -> List[str]:
        """Get all article IDs in a cluster."""
        result = await db.execute(
            select(ArticleCluster.article_id).where(ArticleCluster.cluster_id == cluster_id)
        )
        return [row[0] for row in result.all()]

    async def get_article_cluster(self, article_id: str, db: AsyncSession) -> Optional[int]:
        """Get the cluster ID for an article."""
        result = await db.execute(
            select(ArticleCluster.cluster_id).where(ArticleCluster.article_id == article_id)
        )
        row = result.first()
        return row[0] if row else None

    async def get_all_clusters(self, db: AsyncSession) -> List[dict]:
        """Get all clusters with their member counts."""
        result = await db.execute(select(Cluster))
        clusters = result.scalars().all()

        cluster_list = []
        for c in clusters:
            members = await self.get_cluster_members(c.id, db)
            cluster_list.append({
                "id": c.id,
                "label": c.label,
                "member_count": len(members),
                "article_ids": members,
                "created_at": str(c.created_at),
            })
        return cluster_list
