import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models.article import Article
from app.services.orchestrator import Orchestrator

async def main():
    async with async_session() as db:
        # Check all distinct scopes
        result = await db.execute(select(Article.geographic_scope).distinct())
        scopes = result.scalars().all()
        print(f"Distinct scopes in DB: {scopes}")

        # Check what the Orchestrator returns for region="global"
        from app.services.ingestion_service import IngestionService
        from app.services.entity_service import EntityService
        from app.services.embedding_service import EmbeddingService
        from app.services.clustering_service import ClusteringService
        from app.services.scoring_service import ScoringService
        from app.services.validation_service import ValidationService
        from app.services.llm_service import get_llm_service

        ingestion = IngestionService()
        entity = EntityService()
        embedding = EmbeddingService()
        clustering = ClusteringService(embedding)
        scoring = ScoringService(embedding, entity, clustering)
        validation = ValidationService()
        llm = get_llm_service()

        orc = Orchestrator(ingestion, entity, embedding, clustering, scoring, validation, llm)
        global_articles = await orc.get_recent_news(db, region="global", limit=20)
        
        print("\n=== REGION GLOBAL ARTICLES ===")
        for a in global_articles:
            print(f"ID: {a.id} | Title: {a.title} | Source: {a.source}")

asyncio.run(main())
