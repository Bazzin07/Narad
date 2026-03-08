"""
Narad v2 — GenAI-Powered Event Intelligence Platform
FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, get_db, async_session

# ── Service Instances (module-level singletons) ──────────────────────────────

from app.services.ingestion_service import IngestionService
from app.services.entity_service import EntityService
from app.services.embedding_service import EmbeddingService
from app.services.clustering_service import ClusteringService
from app.services.scoring_service import ScoringService
from app.services.validation_service import ValidationService
from app.services.llm_service import get_llm_service
from app.services.orchestrator import Orchestrator
from app.services.event_intelligence_service import EventIntelligenceService
from app.services.fact_sheet_service import FactSheetService

# Initialize services
ingestion_service = IngestionService()
entity_service = EntityService()
embedding_service = EmbeddingService()
clustering_service = ClusteringService(embedding_service)
scoring_service = ScoringService(embedding_service, entity_service, clustering_service)
validation_service = ValidationService()
llm_service = get_llm_service()

orchestrator = Orchestrator(
    ingestion_service=ingestion_service,
    entity_service=entity_service,
    embedding_service=embedding_service,
    clustering_service=clustering_service,
    scoring_service=scoring_service,
    validation_service=validation_service,
    llm_service=llm_service,
)



event_intelligence_service = EventIntelligenceService(
    embedding_service=embedding_service,
    entity_service=entity_service,
    scoring_service=scoring_service,
    clustering_service=clustering_service,
    llm_service=llm_service,
)

fact_sheet_service = FactSheetService(
    embedding_service=embedding_service,
    entity_service=entity_service,
    scoring_service=scoring_service,
    llm_service=llm_service,
)

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Background Ingestion ──────────────────────────────────────────────────────

_scheduler = None


async def _scheduled_ingestion():
    """Background job: run ingestion pipeline every 30 minutes."""
    from app.database import async_session
    try:
        async with async_session() as db:
            result = await orchestrator.run_full_pipeline(db)
            ingestion = result.get("ingestion", {})
            stored = ingestion.get("articles_stored", 0)
            logger.info(f"⏰ Scheduled ingestion: {stored} new articles stored")
    except Exception as e:
        logger.error(f"⏰ Scheduled ingestion failed: {e}")


# ── Lifespan ──────────────────────────────────────────────────────────────────


async def _rebuild_faiss_from_db():
    """Background task: wait for DB init, then embed all articles into FAISS."""
    import asyncio
    await asyncio.sleep(8)  # Wait for DB init to complete
    try:
        async with async_session() as db:
            count = await embedding_service.rebuild_index(db)
            faiss_count = embedding_service._faiss_index.ntotal if embedding_service._faiss_index else 0
            logger.info(f"✅ FAISS rebuild complete: {count} articles, index has {faiss_count} vectors")
    except Exception as e:
        logger.error(f"FAISS rebuild from DB failed: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global _scheduler
    logger.info("🚀 Narad v2 starting up...")

    # Initialize database in the background so the health endpoint is immediately
    # available for App Runner's health check. DB will be ready within a few seconds.
    import asyncio
    asyncio.create_task(init_db())
    logger.info("✅ Database init started in background")

    # Always initialize FAISS in-memory index (RDS doesn't have pgvector extension)
    embedding_service._ensure_faiss_index()
    embedding_service.load_index()
    faiss_count = embedding_service._faiss_index.ntotal if embedding_service._faiss_index else 0
    logger.info(f"✅ Embedding service ready (FAISS: {faiss_count} vectors)")

    # Background task: rebuild FAISS from existing DB articles
    asyncio.create_task(_rebuild_faiss_from_db())
    logger.info("✅ FAISS rebuild from DB started in background")

    logger.info(f"✅ LLM backend: {settings.llm_backend}")
    logger.info(f"✅ Storage backend: {settings.storage_backend}")
    logger.info(f"✅ Score threshold: {settings.score_threshold}")

    # v2: Start background ingestion scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        _scheduler = AsyncIOScheduler()
        _scheduler.add_job(_scheduled_ingestion, "interval", minutes=30, id="ingestion_cron")
        _scheduler.start()
        logger.info("✅ Background ingestion scheduler started (every 30 min)")
    except ImportError:
        logger.warning("⚠️ APScheduler not installed — background ingestion disabled. Install with: pip install apscheduler")
    except Exception as e:
        logger.warning(f"⚠️ Scheduler failed to start: {e}")

    yield

    # Shutdown
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("✅ Scheduler stopped")
    logger.info("🛑 Narad shutting down...")
    embedding_service.save_index()
    logger.info("✅ FAISS index saved")


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Narad — Event Intelligence Platform",
    description=(
        "GenAI-powered platform that discovers hidden connections between news events. "
        "Deterministic backend detects relationships. Generative AI explains them."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — Starlette CORSMiddleware supports wildcard subdomains via
# "https://*.example.com" patterns (the allow_origin_regex param is NOT
# needed for this form).  However, for maximum reliability with AWS
# services where the subdomain is dynamic, we also set allow_origin_regex
# as a safety net.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://main.dlf5o2e741xry.amplifyapp.com",
    ],
    allow_origin_regex=r"https://.*\.(amplifyapp\.com|awsapprunner\.com|narad\.ai)",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


import time
from collections import defaultdict
from fastapi.responses import JSONResponse

# Simple in-memory rate limiter: 100 requests / 60 seconds per IP
_ip_requests = defaultdict(list)
RATE_LIMIT = 100
RATE_WINDOW = 60

@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    # 1. Rate Limiting
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Clean up old timestamps
    _ip_requests[client_ip] = [t for t in _ip_requests[client_ip] if now - t < RATE_WINDOW]
    
    if len(_ip_requests[client_ip]) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
            headers={"Retry-After": str(RATE_WINDOW)}
        )
    
    _ip_requests[client_ip].append(now)
    
    # 2. Process Request
    response = await call_next(request)
    
    # 3. Security Headers (Defend against cyber attacks: XSS, Clickjacking, MIME sniffing)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Basic CSP - restrict things to same origin mostly
    response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' https:; img-src 'self' data: https:;"
    
    return response

# ── Routes ────────────────────────────────────────────────────────────────────

from app.routes.news_routes import router as news_router
from app.routes.compare_routes import router as compare_router
from app.routes.probe_routes import router as probe_router
from app.routes.chain_routes import router as chain_router
from app.routes.source_routes import router as source_router
from app.routes.analytics_routes import router as analytics_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.chat_routes import router as chat_router

app.include_router(news_router)
app.include_router(compare_router)
app.include_router(probe_router)
app.include_router(chain_router)
app.include_router(source_router)
app.include_router(analytics_router)
app.include_router(dashboard_router)
app.include_router(chat_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "narad",
        "version": "1.0.0",
        "llm_backend": settings.llm_backend,
        "storage_backend": settings.storage_backend,
        "faiss_vectors": embedding_service._faiss_index.ntotal if embedding_service._faiss_index else 0,
    }


@app.get("/")
async def root():
    return {
        "name": "Narad — Event Intelligence Platform",
        "description": "Discover hidden connections between news events",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "news": "/api/news",
            "compare": "/api/compare",
            "probe": "/api/probe (POST) — News Probe",
            "explore": "/api/news/{article_id}/explore (POST) — Event Intelligence",
            "fact_sheet": "/api/news/{article_id}/fact-sheet (GET) — Multi-Source Fact Sheet",
            "source_health": "/api/sources/health (GET) — Source Health Monitor",
            "timeline": "/api/analytics/timeline/{article_id} (GET) — Event Timeline",
            "entity_graph": "/api/analytics/entity-graph/{article_id} (GET) — Knowledge Graph",
            "sentiment_topic": "/api/analytics/sentiment/topic/{topic} (GET) — Sentiment Trends",
            "sentiment_entity": "/api/analytics/sentiment/entity/{name} (GET) — Entity Sentiment",
            "bias_analysis": "/api/analytics/bias/{article_id} (POST) — Source Bias",
            "dashboard_heatmap": "/api/dashboard/heatmap (GET) — India Heatmap",
            "dashboard_briefing": "/api/dashboard/briefing/{state} (POST) — AI State Briefing",
            "dashboard_news": "/api/dashboard/news?state= (GET) — State News",
            "dashboard_markets": "/api/dashboard/markets (GET) — Market Data",
            "live_chat": "/ws/chat (WebSocket) — Live Chat",
            "clusters": "/api/clusters",
            "ingest": "/api/news/ingest (POST)",
        },
    }
