"""
News Probe Routes — Feature 3: User submits news text to find related articles.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import ProbeRequest, ProbeResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["News Probe"])


@router.post("/probe", response_model=ProbeResponse)
async def probe_news(
    request: ProbeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Feature 3: News Probe — submit news text and discover related articles.

    The user provides a piece of news (headline, paragraph, tweet, etc.)
    along with where they found it (source). Narad will:
    1. Detect the language
    2. Extract entities (people, places, orgs)
    3. Search the corpus for related articles
    4. Score and rank the matches
    5. Explain how each match is connected

    Works across languages — submit in Hindi, get matches from English sources too.
    """
    from app.main import orchestrator

    if not request.text or len(request.text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Text must be at least 10 characters long"
        )

    try:
        result = await orchestrator.probe_news(
            text=request.text,
            source=request.source or "User Submission",
            session_id=request.session_id,
            db=db,
            preferred_language=request.preferred_language,
            top_k=request.top_k,
            detailed=request.detailed,
        )
        return result
    except Exception as e:
        logger.error(f"Probe failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Probe failed: {str(e)}")
