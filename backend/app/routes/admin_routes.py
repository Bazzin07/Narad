from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.database import get_db
from app.main import orchestrator

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/ingest", response_model=Dict[str, Any])
async def trigger_ingestion(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger a full ingestion pipeline run in the background."""
    async def run_pipeline():
        from app.database import async_session
        import logging
        logger = logging.getLogger(__name__)
        try:
            async with async_session() as session:
                logger.info("Admin triggered ingestion starting...")
                result = await orchestrator.run_full_pipeline(session)
                logger.info(f"Admin ingestion complete: {result}")
        except Exception as e:
            logger.error(f"Admin ingestion failed: {e}", exc_info=True)
            
    background_tasks.add_task(run_pipeline)
    return {"status": "Ingestion triggered in background"}

@router.post("/fix-scopes")
async def trigger_fix_scopes(
    background_tasks: BackgroundTasks,
):
    """Run the scope fixing script on the production database."""
    async def run_fix():
        import logging
        logger = logging.getLogger(__name__)
        try:
            from fix_scopes import fix_scopes
            await fix_scopes()
            logger.info("Scope fix complete")
        except Exception as e:
            logger.error(f"Scope fix failed: {e}", exc_info=True)
            
    background_tasks.add_task(run_fix)
    return {"status": "Scope fix triggered in background"}
