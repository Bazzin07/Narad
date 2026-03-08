"""
Pydantic request / response schemas for the Narad API.
"""
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


# ── Article Schemas ───────────────────────────────────────────────────────────


class ArticleSummary(BaseModel):
    id: str
    title: str
    source: str
    published_at: str
    language: Optional[str] = "en"
    entities: List[str] = []
    cluster_id: Optional[int] = None
    image_url: Optional[str] = None
    topic: Optional[str] = None

    model_config = {"from_attributes": True}


class ArticleDetail(BaseModel):
    id: str
    title: str
    content: str
    summary: Optional[str] = None
    source: str
    url: str
    published_at: str
    language: Optional[str] = "en"
    entities: List[Dict[str, str]] = []
    cluster_id: Optional[int] = None
    processed: int = 0
    image_url: Optional[str] = None
    topic: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Scoring Schemas ───────────────────────────────────────────────────────────


class RelationScoreSchema(BaseModel):
    total_score: float
    confidence: str
    embedding_similarity: float
    entity_overlap: float
    temporal_proximity: float
    source_diversity: float
    graph_distance: float
    credibility_factor: float = 1.0


class ValidationResultSchema(BaseModel):
    allowed: bool
    reason: str
    score: float
    calls_remaining: int


# ── Compare Schemas ───────────────────────────────────────────────────────────


class CompareRequest(BaseModel):
    article1_id: str
    article2_id: str
    session_id: str = "default"
    preferred_language: str = "en"
    detailed: bool = False  # False=overview, True=deep analysis


class CompareResponse(BaseModel):
    article1: ArticleSummary
    article2: ArticleSummary
    relation_score: RelationScoreSchema
    shared_entities: List[str]
    overview: Optional[str] = None  # Tier 1: quick summary
    explanation: Optional[str] = None  # Tier 2: deep analysis (only when detailed=True)
    validation: ValidationResultSchema


# ── Ingestion Schemas ─────────────────────────────────────────────────────────


class IngestResponse(BaseModel):
    status: str
    articles_fetched: int
    articles_stored: int
    articles_skipped: int
    errors: List[str] = []


# ── Probe Schemas (Feature 3) ────────────────────────────────────────────────


class ProbeRequest(BaseModel):
    """User-submitted news text to check against the existing corpus."""
    text: str  # The news content / headline / description
    source: Optional[str] = "User Submission"  # Where the user found this news
    source_url: Optional[str] = None  # Optional link
    session_id: str = "default"
    detailed: bool = False  # False=overview map, True=deep per-match analysis
    preferred_language: str = "English"
    top_k: int = 5  # Number of matches to return


class ProbeMatchSchema(BaseModel):
    """A single match from the corpus."""
    article: ArticleSummary
    relation_score: RelationScoreSchema
    shared_entities: List[str] = []
    explanation: Optional[str] = None


class ProbeResponse(BaseModel):
    """Response for the news probe feature."""
    query_text: str
    query_source: str
    detected_language: str
    extracted_entities: List[str] = []
    matches: List[ProbeMatchSchema]
    total_matches_found: int
    overview_map: Optional[str] = None  # Tier 1: connection map visualization
    analysis_summary: Optional[str] = None

