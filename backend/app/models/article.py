"""
SQLAlchemy ORM models for Narad.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Float, Integer, DateTime, Boolean,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship, DeclarativeBase
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    Vector = None
    PGVECTOR_AVAILABLE = False


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ── Source Registry ───────────────────────────────────────────────────────────


class Source(Base):
    """Registered news/data source with credibility and language metadata."""
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    base_url = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=False, default="news")  # news, gov, report, video, tweet
    language = Column(String(10), nullable=False, default="en")
    credibility_weight = Column(Float, nullable=False, default=1.0)  # 0.0–1.0
    source_region = Column(String(20), nullable=False, default="india")  # "india" or "global"
    poll_interval = Column(Integer, default=3600)  # seconds between polls
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Health monitoring fields
    last_fetched_at = Column(DateTime, nullable=True)              # last time we attempted fetch
    last_success_at = Column(DateTime, nullable=True)              # last time we got ≥ 1 article
    consecutive_failures = Column(Integer, default=0)              # reset on success
    total_fetches = Column(Integer, default=0)                     # all-time fetch attempts
    total_articles_fetched = Column(Integer, default=0)            # all-time articles from this source

    articles = relationship("Article", back_populates="source_ref")

    __table_args__ = (
        Index("idx_sources_active", "active"),
        Index("idx_sources_type", "source_type"),
        Index("idx_sources_region", "source_region"),
    )


# ── Articles ──────────────────────────────────────────────────────────────────


class Article(Base):
    __tablename__ = "articles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    source = Column(String(255), nullable=False)  # backward-compat string name
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=True)  # FK to source registry
    url = Column(Text, unique=True, nullable=False)
    published_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    s3_key = Column(Text, nullable=True)
    processed = Column(Integer, default=0)  # 0=raw, 1=entities, 2=embedded, 3=clustered
    language = Column(String(10), nullable=True, default="en")
    credibility_weight = Column(Float, nullable=False, default=1.0)
    topic = Column(String(50), nullable=True, default="general")  # military, economy, politics, etc.
    content_hash = Column(String(64), nullable=True)  # SHA-256 of title+first_300_chars
    image_url = Column(Text, nullable=True)  # extracted from RSS media:content, enclosure, og:image
    geographic_scope = Column(String(10), nullable=True, default="global")  # india, global, mixed
    state = Column(String(50), nullable=True)  # indian state: delhi, maharashtra, etc.
    sentiment_score = Column(Float, nullable=True)  # -1.0 (negative) to 1.0 (positive)
    embedding = Column(Text, nullable=True)  # Serialized embedding (FAISS handles similarity search)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    source_ref = relationship("Source", back_populates="articles")
    entity_associations = relationship("ArticleEntity", back_populates="article", cascade="all, delete-orphan")
    cluster_associations = relationship("ArticleCluster", back_populates="article", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_articles_published", "published_at"),
        Index("idx_articles_source", "source"),
        Index("idx_articles_processed", "processed"),
        Index("idx_articles_language", "language"),
        Index("idx_articles_content_hash", "content_hash"),
        Index("idx_articles_source_id", "source_id"),
        Index("idx_articles_source_id_published", "source_id", "published_at"),
        Index("idx_articles_geo_scope", "geographic_scope"),
        Index("idx_articles_geo_scope_published", "geographic_scope", "published_at"),
        Index("idx_articles_state", "state"),
    )


# ── Entities ──────────────────────────────────────────────────────────────────


class Entity(Base):
    __tablename__ = "entities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    text = Column(String(255), nullable=False)
    normalized_text = Column(String(255), nullable=True)  # transliterated latin form for cross-lingual matching
    type = Column(String(50), nullable=False)  # PERSON, ORG, GPE
    created_at = Column(DateTime, default=datetime.utcnow)

    article_associations = relationship("ArticleEntity", back_populates="entity", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("text", "type", name="uq_entity_text_type"),
        Index("idx_entities_type", "type"),
        Index("idx_entities_normalized", "normalized_text"),
    )


# ── Article ↔ Entity Association ──────────────────────────────────────────────


class ArticleEntity(Base):
    __tablename__ = "article_entities"

    article_id = Column(String(36), ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)

    article = relationship("Article", back_populates="entity_associations")
    entity = relationship("Entity", back_populates="article_associations")


# ── Clusters ──────────────────────────────────────────────────────────────────


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    article_associations = relationship("ArticleCluster", back_populates="cluster", cascade="all, delete-orphan")


# ── Article ↔ Cluster Association ─────────────────────────────────────────────


class ArticleCluster(Base):
    __tablename__ = "article_clusters"

    article_id = Column(String(36), ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id", ondelete="CASCADE"), primary_key=True)

    article = relationship("Article", back_populates="cluster_associations")
    cluster = relationship("Cluster", back_populates="article_associations")


# ── Bedrock Call Tracking ─────────────────────────────────────────────────────


class BedrockCall(Base):
    __tablename__ = "bedrock_calls"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(255), nullable=False)
    article1_id = Column(String(36), ForeignKey("articles.id"), nullable=True)
    article2_id = Column(String(36), ForeignKey("articles.id"), nullable=True)
    relation_score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_bedrock_session", "session_id"),
    )


# ── Narrative Cache (v2) ──────────────────────────────────────────────────────


class NarrativeCache(Base):
    """
    Cache for LLM-generated narratives.
    Key: article_id + mode + language
    Invalidated when articles are updated or clusters change.
    """
    __tablename__ = "narrative_cache"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    article_id = Column(String(36), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    mode = Column(String(50), nullable=False)  # "deep_analysis", "impact_analysis", "overview"
    language = Column(String(10), nullable=False, default="en")
    cached_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # TTL-based invalidation

    __table_args__ = (
        Index("idx_narrative_cache_lookup", "article_id", "mode", "language"),
    )
