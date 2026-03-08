"""
Narad Configuration — loaded from environment variables / .env file.
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://ayushgourav@localhost/narad"

    # ── Storage ───────────────────────────────────────────────
    storage_backend: str = "local"  # "local" or "s3"
    local_storage_path: str = "./data/raw_articles"
    s3_bucket: str = "narad-raw-articles"

    # ── AWS ───────────────────────────────────────────────────
    aws_region: str = "us-east-1"
    # ── Model: Ask Narad + Situation Room (fast, great multilingual Indian langs)
    # Cross-region inference profile required by Bedrock for Llama 3.3+
    bedrock_model_id_llama: str = "us.meta.llama3-3-70b-instruct-v1:0"
    # ── Model: Narrative Conflicts + Cross-Validation (structured reasoning, JSON)
    # Cross-region inference profile required by Bedrock for DeepSeek V3.2
    bedrock_model_id_deepseek: str = "deepseek.v3.2"
    # ── Model: Multilingual fallback (best South Indian language coverage)
    bedrock_model_id_fallback: str = "us.amazon.nova-pro-v1:0"
    # ── Legacy fields kept for LLMService compatibility
    bedrock_model_id: str = "us.meta.llama3-3-70b-instruct-v1:0"
    bedrock_model_id_fast: str = "us.meta.llama3-3-70b-instruct-v1:0"

    # ── LLM ───────────────────────────────────────────────────
    llm_backend: str = "bedrock"  # "mock" or "bedrock"

    # ── Ingestion ─────────────────────────────────────────────
    rss_feeds: str = (
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml,"
        "https://feeds.bbci.co.uk/news/world/rss.xml,"
        "https://rss.cnn.com/rss/edition_world.rss"
    )
    news_api_key: str = ""
    news_api_url: str = "https://newsapi.org/v2/top-headlines"

    # ── FAISS ─────────────────────────────────────────────────
    faiss_index_path: str = "./data/faiss_index"

    # ── Validation ────────────────────────────────────────────
    score_threshold: float = 0.60
    max_calls_per_session: int = 10

    # ── Embedding ─────────────────────────────────────────────
    embedding_backend: str = "local"  # "local" or "titan" (set EMBEDDING_BACKEND=titan on AWS)
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384
    titan_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    # ── Language ──────────────────────────────────────────────
    default_language: str = "en"

    @property
    def rss_feed_list(self) -> List[str]:
        return [f.strip() for f in self.rss_feeds.split(",") if f.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
