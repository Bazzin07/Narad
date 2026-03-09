"""
Narad Database — async SQLAlchemy engine + session factory.
Uses PostgreSQL via asyncpg driver.
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=15,          # bumped from 10 — handles concurrent requests better
    max_overflow=10,       # reduced from 20 — prevents pool explosion
    pool_timeout=10,       # fail fast if pool exhausted (10s wait max)
    pool_recycle=1800,     # recycle connections every 30 min to avoid stale
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create all tables using raw SQL to avoid pgvector type introspection issues."""
    from sqlalchemy import text as sa_text

    async with engine.begin() as conn:
        # Try enabling pgvector extension (optional — FAISS fallback used if unavailable)
        try:
            await conn.execute(sa_text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("pgvector extension enabled")
        except Exception as e:
            logger.warning(f"pgvector extension not available: {e}. FAISS fallback will be used.")

        # Create tables with explicit SQL — avoids SQLAlchemy introspecting `vector` type
        try:
            await conn.execute(sa_text("""
                CREATE TABLE IF NOT EXISTS sources (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    base_url TEXT NOT NULL,
                    source_type VARCHAR(50) NOT NULL DEFAULT 'news',
                    language VARCHAR(10) NOT NULL DEFAULT 'en',
                    credibility_weight FLOAT NOT NULL DEFAULT 1.0,
                    source_region VARCHAR(20) NOT NULL DEFAULT 'india',
                    poll_interval INTEGER DEFAULT 3600,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_fetched_at TIMESTAMP,
                    last_success_at TIMESTAMP,
                    consecutive_failures INTEGER DEFAULT 0,
                    total_fetches INTEGER DEFAULT 0,
                    total_articles_fetched INTEGER DEFAULT 0
                )
            """))

            await conn.execute(sa_text("""
                CREATE TABLE IF NOT EXISTS articles (
                    id VARCHAR(36) PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    source VARCHAR(255) NOT NULL,
                    source_id VARCHAR(36) REFERENCES sources(id),
                    url TEXT UNIQUE NOT NULL,
                    published_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    s3_key TEXT,
                    processed INTEGER DEFAULT 0,
                    language VARCHAR(10) DEFAULT 'en',
                    credibility_weight FLOAT NOT NULL DEFAULT 1.0,
                    topic VARCHAR(50) DEFAULT 'general',
                    content_hash VARCHAR(64),
                    image_url TEXT,
                    geographic_scope VARCHAR(10) DEFAULT 'global',
                    state VARCHAR(50),
                    sentiment_score FLOAT,
                    embedding TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))

            await conn.execute(sa_text("""
                CREATE TABLE IF NOT EXISTS entities (
                    id VARCHAR(36) PRIMARY KEY,
                    text VARCHAR(255) NOT NULL,
                    normalized_text VARCHAR(255),
                    type VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(text, type)
                )
            """))

            await conn.execute(sa_text("""
                CREATE TABLE IF NOT EXISTS article_entities (
                    article_id VARCHAR(36) REFERENCES articles(id) ON DELETE CASCADE,
                    entity_id VARCHAR(36) REFERENCES entities(id) ON DELETE CASCADE,
                    PRIMARY KEY (article_id, entity_id)
                )
            """))

            await conn.execute(sa_text("""
                CREATE TABLE IF NOT EXISTS clusters (
                    id SERIAL PRIMARY KEY,
                    label VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))

            await conn.execute(sa_text("""
                CREATE TABLE IF NOT EXISTS article_clusters (
                    article_id VARCHAR(36) REFERENCES articles(id) ON DELETE CASCADE,
                    cluster_id INTEGER REFERENCES clusters(id) ON DELETE CASCADE,
                    PRIMARY KEY (article_id, cluster_id)
                )
            """))

            await conn.execute(sa_text("""
                CREATE TABLE IF NOT EXISTS bedrock_calls (
                    id VARCHAR(36) PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    article1_id VARCHAR(36) REFERENCES articles(id),
                    article2_id VARCHAR(36) REFERENCES articles(id),
                    relation_score FLOAT NOT NULL,
                    explanation TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))

            await conn.execute(sa_text("""
                CREATE TABLE IF NOT EXISTS narrative_cache (
                    id VARCHAR(36) PRIMARY KEY,
                    article_id VARCHAR(36) REFERENCES articles(id) ON DELETE CASCADE,
                    mode VARCHAR(50) NOT NULL,
                    language VARCHAR(10) NOT NULL DEFAULT 'en',
                    cached_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP
                )
            """))

            # Indexes
            await conn.execute(sa_text("CREATE INDEX IF NOT EXISTS idx_articles_published ON articles (published_at)"))
            await conn.execute(sa_text("CREATE INDEX IF NOT EXISTS idx_articles_source ON articles (source)"))
            await conn.execute(sa_text("CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles (processed)"))
            await conn.execute(sa_text("CREATE INDEX IF NOT EXISTS idx_articles_language ON articles (language)"))
            await conn.execute(sa_text("CREATE INDEX IF NOT EXISTS idx_articles_content_hash ON articles (content_hash)"))
            await conn.execute(sa_text("CREATE INDEX IF NOT EXISTS idx_articles_geo_scope ON articles (geographic_scope)"))
            await conn.execute(sa_text("CREATE INDEX IF NOT EXISTS idx_articles_geo_scope_published ON articles (geographic_scope, published_at)"))
            await conn.execute(sa_text("CREATE INDEX IF NOT EXISTS idx_articles_state ON articles (state)"))
            await conn.execute(sa_text("CREATE INDEX IF NOT EXISTS idx_sources_active ON sources (active)"))
            await conn.execute(sa_text("CREATE INDEX IF NOT EXISTS idx_narrative_cache_lookup ON narrative_cache (article_id, mode, language)"))
            await conn.execute(sa_text("CREATE INDEX IF NOT EXISTS idx_bedrock_session ON bedrock_calls (session_id)"))

            # Ensure new columns exist on older DB schemas (safe migrations)
            for col_sql in [
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS geographic_scope VARCHAR(10) DEFAULT 'global'",
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS sentiment_score FLOAT",
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS state VARCHAR(50)",
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS embedding TEXT",
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS image_url TEXT",
            ]:
                try:
                    await conn.execute(sa_text(col_sql))
                except Exception:
                    pass

            logger.info("✅ Database tables created/verified via raw SQL")
        except Exception as e:
            logger.error(f"DB init failed: {e}", exc_info=True)



async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
