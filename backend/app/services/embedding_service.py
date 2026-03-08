"""
Embedding Service — multilingual embeddings + pgvector storage.

Backends:
  - "local": paraphrase-multilingual-MiniLM-L12-v2 (384-dim, 50+ languages, free)
  - "titan": Amazon Titan Text Embeddings V2 via Bedrock (configurable dim)

Vector Storage:
  - PRIMARY: pgvector column on Article table (works on AWS RDS PostgreSQL)
  - FALLBACK: in-memory FAISS index (for local dev without pgvector)

Cross-lingual: Hindi article and English article about the same event
will have high cosine similarity — no translation needed.
"""
import logging
import os
import json
from typing import List, Tuple, Optional

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.config import settings

logger = logging.getLogger(__name__)

# Lazy-load models
_model = None
_faiss_module = None
_bedrock_client = None

# Detect pgvector availability
try:
    from pgvector.sqlalchemy import Vector  # noqa: F401
    PGVECTOR_AVAILABLE = True
    logger.info("pgvector available — using DB-backed vector search")
except ImportError:
    PGVECTOR_AVAILABLE = False
    logger.warning("pgvector not installed — using in-memory FAISS fallback")


def _get_model():
    """Load local multilingual sentence-transformer model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.embedding_model)
        logger.info(f"Loaded embedding model: {settings.embedding_model}")
    return _model


def _get_faiss():
    global _faiss_module
    if _faiss_module is None:
        try:
            import faiss as faiss_lib
            _faiss_module = faiss_lib
        except ImportError:
            _faiss_module = None
    return _faiss_module


def _get_bedrock():
    """Get Bedrock client for Titan embeddings."""
    global _bedrock_client
    if _bedrock_client is None:
        import boto3
        _bedrock_client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    return _bedrock_client


class EmbeddingService:
    """
    Generates multilingual embeddings and manages vector storage.

    Storage strategy:
      - If pgvector is available (production on AWS RDS): embeddings stored
        directly in the articles.embedding column. No local files needed.
      - If pgvector is unavailable (local dev): falls back to in-memory FAISS
        index persisted on disk.
    """

    def __init__(self):
        self.backend = settings.embedding_backend  # "local" or "titan"
        # Compute effective dimension: Titan V2 only supports 256, 512, 1024
        raw_dim = settings.embedding_dim
        if self.backend == "titan":
            valid_dims = [256, 512, 1024]
            self.dim = min(valid_dims, key=lambda d: abs(d - raw_dim))
        else:
            self.dim = raw_dim
        self.index_path = settings.faiss_index_path

        # FAISS fallback (local dev only)
        self._faiss_index = None
        self._faiss_article_ids: List[str] = []
        self._id_map_path = os.path.join(self.index_path, "id_map.json")

    # ── Embedding Generation ───────────────────────────────────────────────────

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding vector. Routes to local model or Titan based on config."""
        if self.backend == "titan":
            return self._generate_titan(text)
        return self._generate_local(text)

    def _generate_local(self, text: str) -> np.ndarray:
        """Generate embedding using local multilingual model."""
        model = _get_model()
        if len(text) > 10_000:
            text = text[:10_000]
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.astype(np.float32)

    def _generate_titan(self, text: str) -> np.ndarray:
        """Generate embedding using Amazon Titan via Bedrock."""
        import json as json_mod
        client = _get_bedrock()

        if len(text) > 8_000:
            text = text[:8_000]

        # Titan Embed V2 accepts inputText, dimensions (256|512|1024), normalize
        titan_dim = int(self.dim)
        # Titan V2 only supports 256, 512, or 1024 — clamp to nearest valid
        valid_dims = [256, 512, 1024]
        if titan_dim not in valid_dims:
            titan_dim = min(valid_dims, key=lambda d: abs(d - titan_dim))
        body = json_mod.dumps({
            "inputText": text,
            "dimensions": titan_dim,
            "normalize": True,
        })

        try:
            response = client.invoke_model(
                modelId=settings.titan_embedding_model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            result = json_mod.loads(response["body"].read())
            embedding = np.array(result["embedding"], dtype=np.float32)
            return embedding
        except Exception as e:
            logger.error(f"Titan embedding failed, falling back to local: {e}")
            return self._generate_local(text)

    # ── pgvector Storage (Primary — AWS Production) ────────────────────────────

    async def store_embedding_db(self, article_id: str, embedding: np.ndarray, db: AsyncSession) -> bool:
        """Store embedding directly in the articles table via pgvector."""
        if not PGVECTOR_AVAILABLE:
            return False
        try:
            embedding_list = embedding.tolist()
            await db.execute(
                text("UPDATE articles SET embedding = :emb WHERE id = :id"),
                {"emb": embedding_list, "id": article_id}
            )
            return True
        except Exception as e:
            logger.error(f"pgvector store failed for {article_id}: {e}")
            return False

    async def find_similar_db(self, embedding: np.ndarray, k: int = 10, db: AsyncSession = None) -> List[Tuple[str, float]]:
        """Find similar articles using pgvector cosine similarity search."""
        if not PGVECTOR_AVAILABLE or db is None:
            return []
        try:
            embedding_list = embedding.tolist()
            result = await db.execute(
                text("""
                    SELECT id, 1 - (embedding <=> CAST(:emb AS vector)) AS similarity
                    FROM articles
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:emb AS vector)
                    LIMIT :k
                """),
                {"emb": str(embedding_list), "k": k}
            )
            rows = result.fetchall()
            return [(row[0], float(row[1])) for row in rows]
        except Exception as e:
            logger.error(f"pgvector search failed: {e}")
            return []

    # ── FAISS Fallback (Local Dev Only) ────────────────────────────────────────

    def _ensure_faiss_index(self):
        """Ensure in-memory FAISS index is initialized (local dev fallback)."""
        if self._faiss_index is None:
            faiss = _get_faiss()
            if faiss:
                self._faiss_index = faiss.IndexFlatIP(self.dim)
                logger.info(f"Initialized in-memory FAISS index (dim={self.dim}) for local dev")

    def _add_to_faiss(self, article_id: str, embedding: np.ndarray) -> int:
        """Add embedding to in-memory FAISS index."""
        self._ensure_faiss_index()
        if not self._faiss_index:
            return -1

        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        embedding = embedding.reshape(1, -1).astype(np.float32)
        self._faiss_index.add(embedding)
        self._faiss_article_ids.append(article_id)
        return len(self._faiss_article_ids) - 1

    def _find_similar_faiss(self, embedding: np.ndarray, k: int = 10) -> List[Tuple[str, float]]:
        """Find similar articles using in-memory FAISS (local dev fallback)."""
        self._ensure_faiss_index()
        if not self._faiss_index or self._faiss_index.ntotal == 0:
            return []

        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        embedding = embedding.reshape(1, -1).astype(np.float32)
        k = min(k, self._faiss_index.ntotal)
        scores, indices = self._faiss_index.search(embedding, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._faiss_article_ids):
                results.append((self._faiss_article_ids[idx], float(score)))
        return results

    # ── Public API ─────────────────────────────────────────────────────────────

    async def find_similar(self, embedding: np.ndarray, k: int = 10, db: AsyncSession = None) -> List[Tuple[str, float]]:
        """
        Find k most similar articles. Uses pgvector if available, falls back to FAISS.
        """
        if PGVECTOR_AVAILABLE and db is not None:
            results = await self.find_similar_db(embedding, k, db)
            if results:
                return results

        # Fallback: in-memory FAISS
        return self._find_similar_faiss(embedding, k)

    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))

    async def process_article(self, article: Article, db: AsyncSession) -> Optional[np.ndarray]:
        """Generate embedding for an article and store it appropriately."""
        try:
            full_text = f"{article.title}. {article.content}"
            embedding = self.generate_embedding(full_text)

            # Always add to FAISS in-memory index (RDS doesn't have pgvector extension)
            self._add_to_faiss(article.id, embedding)

            article.processed = max(article.processed, 2)
            await db.flush()
            return embedding
        except Exception as e:
            logger.error(f"Embedding failed for article {article.id}: {e}")
            return None

    async def rebuild_index(self, db: AsyncSession) -> int:
        """Rebuild FAISS index from all articles in the DB.
        
        The DB fetch runs on the async thread. The CPU-heavy embedding loop
        is offloaded to a thread-pool executor via asyncio.to_thread so the
        event loop is never blocked and the server remains responsive.
        """
        import asyncio
        from sqlalchemy import text as sa_text

        # --- async: fetch rows from DB ---
        result = await db.execute(
            sa_text("SELECT id, title, content FROM articles ORDER BY created_at")
        )
        rows = result.fetchall()

        # Reset in-memory FAISS (sync, trivial)
        self._faiss_index = None
        self._faiss_article_ids = []
        self._ensure_faiss_index()

        # --- thread: generate embeddings without blocking the event loop ---
        def _embed_all():
            count = 0
            for row in rows:
                try:
                    art_id, title, content = row[0], row[1], row[2]
                    full_text = f"{title}. {content}"
                    embedding = self.generate_embedding(full_text)
                    self._add_to_faiss(art_id, embedding)
                    count += 1
                except Exception as e:
                    logger.error(f"Rebuild: embedding failed for {row[0]}: {e}")
            return count

        count = await asyncio.to_thread(_embed_all)
        logger.info(f"Rebuilt FAISS index: {count}/{len(rows)} articles embedded")
        return count


    async def process_unprocessed(self, db: AsyncSession, limit: int = 50) -> int:
        """Generate embeddings for articles that don't have them yet.
        
        Embedding generation is CPU-bound. We offload the inner loop to a
        thread-pool executor so the event loop stays free during batch runs.
        """
        import asyncio

        result = await db.execute(
            select(Article).where(Article.processed < 2).limit(limit)
        )
        articles = result.scalars().all()

        # Each article's embedding is generated synchronously by the model.
        # We wrap the whole loop in to_thread so it doesn't freeze the event loop.
        def _embed_articles():
            count = 0
            for article in articles:
                try:
                    full_text = f"{article.title}. {article.content or ''}"
                    embedding = self.generate_embedding(full_text)
                    self._add_to_faiss(article.id, embedding)
                    article.processed = 2
                    count += 1
                except Exception as e:
                    logger.error(f"Embedding failed for {article.id}: {e}")
            return count

        count = await asyncio.to_thread(_embed_articles)

        if count > 0 and not PGVECTOR_AVAILABLE:
            self.save_faiss_index()
            await db.commit()
        elif count > 0:
            await db.commit()

        logger.info(f"Embedding: processed {count}/{len(articles)} articles")
        return count


    # ── FAISS Disk Persistence (Local Dev Only) ────────────────────────────────

    def save_faiss_index(self) -> None:
        """Persist FAISS index to disk (local dev only — not needed in production with pgvector)."""
        if PGVECTOR_AVAILABLE:
            return  # Not needed; pgvector is authoritative
        self._ensure_faiss_index()
        if not self._faiss_index:
            return
        faiss = _get_faiss()
        if not faiss:
            return
        os.makedirs(self.index_path, exist_ok=True)
        index_file = os.path.join(self.index_path, "index.faiss")
        faiss.write_index(self._faiss_index, index_file)
        with open(self._id_map_path, "w") as f:
            json.dump(self._faiss_article_ids, f)
        logger.info(f"Saved FAISS index ({self._faiss_index.ntotal} vectors) to {self.index_path}")

    def load_faiss_index(self) -> bool:
        """Load FAISS index from disk (local dev fallback)."""
        if PGVECTOR_AVAILABLE:
            return True  # pgvector is authoritative; skip FAISS loading
        faiss = _get_faiss()
        if not faiss:
            return False
        index_file = os.path.join(self.index_path, "index.faiss")
        if not os.path.exists(index_file) or not os.path.exists(self._id_map_path):
            logger.info("No existing FAISS index found — starting fresh")
            self._ensure_faiss_index()
            return False
        try:
            self._faiss_index = faiss.read_index(index_file)
            with open(self._id_map_path, "r") as f:
                self._faiss_article_ids = json.load(f)
            logger.info(f"Loaded FAISS index ({self._faiss_index.ntotal} vectors) from {self.index_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}. Starting fresh.")
            self._ensure_faiss_index()
            self._faiss_article_ids = []
            return False

    # Backward-compat alias
    def load_index(self) -> bool:
        return self.load_faiss_index()

    def save_index(self) -> None:
        self.save_faiss_index()

    def add_to_index(self, article_id: str, embedding: np.ndarray) -> int:
        """Backward compat: add to in-memory FAISS index."""
        return self._add_to_faiss(article_id, embedding)

    def get_embedding_by_id(self, article_id: str) -> Optional[np.ndarray]:
        """Retrieve embedding from in-memory FAISS (local dev only)."""
        if article_id not in self._faiss_article_ids:
            return None
        idx = self._faiss_article_ids.index(article_id)
        faiss = _get_faiss()
        if not faiss or not self._faiss_index:
            return None
        embedding = faiss.rev_swig_ptr(self._faiss_index.get_xb(), self._faiss_index.ntotal * self.dim)
        embedding = embedding.reshape(self._faiss_index.ntotal, self.dim)
        return embedding[idx].copy()
