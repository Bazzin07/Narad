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
    """Create all tables (dev convenience — use Alembic in prod)."""
    from app.models.article import Base as ModelBase  # noqa: F811
    async with engine.begin() as conn:
        # Enable pgvector extension (requires PostgreSQL with vector extension installed)
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            logger.warning(f"pgvector extension not available: {e}. FAISS fallback will be used.")

        await conn.run_sync(ModelBase.metadata.create_all)

        # Ensure new columns exist on existing databases (migrations)
        from sqlalchemy import text
        try:
            await conn.execute(text(
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS geographic_scope VARCHAR(10) DEFAULT 'global'"
            ))
            await conn.execute(text(
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS sentiment_score FLOAT"
            ))
            await conn.execute(text(
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS state VARCHAR(50)"
            ))
            # pgvector embedding column (only added when pgvector is available)
            await conn.execute(text(
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS embedding vector(384)"
            ))
            # pgvector similarity search index (cosine distance)
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_articles_embedding ON articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
            ))
            # Add indexes if not present (safe — IF NOT EXISTS)
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_articles_geo_scope ON articles (geographic_scope)"
            ))
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_articles_geo_scope_published ON articles (geographic_scope, published_at)"
            ))
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_articles_state ON articles (state)"
            ))
        except Exception:
            pass  # Column already exists or unsupported DB


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
