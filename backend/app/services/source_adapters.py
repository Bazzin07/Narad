"""
Source Adapters — modular ingestion from multiple data source types.

Architecture:
  BaseSourceAdapter (abstract)
    ├── RSSAdapter        — standard RSS/Atom feeds (existing)
    ├── NewsAPIAdapter    — NewsAPI.org and compatible REST APIs
    ├── JSONFeedAdapter   — structured JSON feeds (e.g., jsonfeed.org)
    └── GovernmentAPIAdapter — gov press release APIs

All adapters normalize output to the same schema before storage.
The ingestion pipeline routes to the correct adapter based on `source_type`.
"""
import re
import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.models.article import Source

logger = logging.getLogger(__name__)


# ── Shared Utilities ──────────────────────────────────────────────────────────

def _content_hash(title: str, content: str) -> str:
    """SHA-256 of title + first 300 chars of content."""
    raw = f"{title.strip().lower()}|{content[:300].strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _detect_language_safe(text: str) -> str:
    """Detect language, falling back to 'en'."""
    try:
        from langdetect import detect
        return detect(text[:1000]) or "en"
    except Exception:
        return "en"


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ── Normalized Article Schema ─────────────────────────────────────────────────

NORMALIZED_FIELDS = {
    "title", "content", "summary", "source", "source_id", "source_type",
    "url", "published_at", "language", "credibility_weight",
    "content_hash", "topic", "image_url", "source_region",
}


# ── Base Adapter ──────────────────────────────────────────────────────────────

class BaseSourceAdapter(ABC):
    """Abstract base for all source adapters."""

    adapter_type: str = "base"

    @abstractmethod
    async def fetch(
        self, source: Source, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch articles from this source.
        Returns a list of normalized article dicts.
        """
        ...

    def _normalize(
        self,
        title: str,
        content: str,
        url: str,
        published_at: datetime,
        source: Source,
        image_url: Optional[str] = None,
        extra_fields: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize any article into the standard schema.
        All adapters MUST call this before returning.
        """
        title = title.strip()
        if not title or not url:
            return None

        content = _strip_html(content).strip()
        if not content or len(content) < 30:
            content = title

        from app.services.ingestion_service import _sanitize_content
        content = _sanitize_content(content)

        lang = source.language or _detect_language_safe(f"{title}. {content}")
        chash = _content_hash(title, content)

        from app.services.topic_classifier import get_primary_topic
        topic = get_primary_topic(title, content, lang)

        result = {
            "title": title,
            "content": content,
            "summary": content[:500] if len(content) > 500 else content,
            "source": source.name,
            "source_id": source.id,
            "source_type": source.source_type,
            "url": url,
            "published_at": published_at,
            "language": lang,
            "credibility_weight": source.credibility_weight or 1.0,
            "content_hash": chash,
            "topic": topic,
            "image_url": image_url,
            "source_region": source.source_region or "global",
        }

        if extra_fields:
            result.update(extra_fields)

        return result


# ── RSS Adapter ───────────────────────────────────────────────────────────────

class RSSAdapter(BaseSourceAdapter):
    """Fetches from RSS/Atom feeds (existing logic)."""

    adapter_type = "rss"

    async def fetch(self, source: Source, **kwargs) -> List[Dict[str, Any]]:
        """Delegates to the existing IngestionService RSS logic."""
        # This adapter wraps the existing RSS fetch to maintain compatibility
        # The actual RSS parsing is still in IngestionService for backward compat
        import feedparser
        from time import mktime

        articles = []
        try:
            feed = feedparser.parse(source.base_url)

            for entry in feed.entries:
                try:
                    title = entry.get("title", "").strip()
                    if not title:
                        continue

                    # Extract content
                    content = ""
                    if hasattr(entry, "content") and entry.content:
                        content = entry.content[0].get("value", "")
                    elif hasattr(entry, "summary"):
                        content = entry.get("summary", "")
                    elif hasattr(entry, "description"):
                        content = entry.get("description", "")

                    if not content or len(content) < 30:
                        if hasattr(entry, "media_description"):
                            content = entry.media_description or ""

                    # Parse date
                    published_at = datetime.utcnow()
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published_at = datetime.fromtimestamp(mktime(entry.published_parsed))
                        except Exception:
                            pass

                    url = entry.get("link", "")
                    if not url:
                        continue

                    # Image
                    image_url = self._extract_image(entry)

                    normalized = self._normalize(
                        title=title,
                        content=content,
                        url=url,
                        published_at=published_at,
                        source=source,
                        image_url=image_url,
                    )
                    if normalized:
                        articles.append(normalized)

                except Exception as e:
                    logger.warning(f"RSS entry normalization failed: {e}")
                    continue

            logger.info(f"[RSS] {source.name}: {len(articles)} articles")
        except Exception as e:
            logger.error(f"[RSS] {source.name} failed: {e}")

        return articles

    def _extract_image(self, entry) -> Optional[str]:
        """Extract image from RSS entry."""
        # media:content
        if hasattr(entry, "media_content") and entry.media_content:
            for mc in entry.media_content:
                url = mc.get("url", "")
                if url and any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                    return url
                if mc.get("medium") == "image" and url:
                    return url

        # media:thumbnail
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            for mt in entry.media_thumbnail:
                url = mt.get("url", "")
                if url:
                    return url

        # enclosures
        if hasattr(entry, "enclosures") and entry.enclosures:
            for enc in entry.enclosures:
                if enc.get("type", "").startswith("image"):
                    return enc.get("href") or enc.get("url", "")

        return None


# ── NewsAPI Adapter ───────────────────────────────────────────────────────────

class NewsAPIAdapter(BaseSourceAdapter):
    """Fetches from NewsAPI.org or compatible REST APIs."""

    adapter_type = "newsapi"

    async def fetch(self, source: Source, **kwargs) -> List[Dict[str, Any]]:
        from app.config import settings

        api_key = settings.news_api_key
        if not api_key:
            logger.info("[NewsAPI] No API key configured — skipping")
            return []

        articles = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {
                    "category": kwargs.get("category", "general"),
                    "country": kwargs.get("country", "in"),
                    "apiKey": api_key,
                    "pageSize": 50,
                }
                response = await client.get(
                    source.base_url or settings.news_api_url,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                for item in data.get("articles", []):
                    try:
                        title = (item.get("title") or "").strip()
                        url = (item.get("url") or "").strip()
                        if not title or not url:
                            continue

                        content = item.get("content") or item.get("description") or title
                        content = re.sub(r"\[\+\d+ chars\]$", "", content).strip()

                        published_at = datetime.utcnow()
                        if item.get("publishedAt"):
                            try:
                                published_at = datetime.fromisoformat(
                                    item["publishedAt"].replace("Z", "+00:00")
                                )
                                published_at = published_at.replace(tzinfo=None)
                            except Exception:
                                pass

                        image_url = item.get("urlToImage")

                        normalized = self._normalize(
                            title=title,
                            content=content,
                            url=url,
                            published_at=published_at,
                            source=source,
                            image_url=image_url,
                        )
                        if normalized:
                            articles.append(normalized)

                    except Exception as e:
                        logger.warning(f"[NewsAPI] Article normalization failed: {e}")

            logger.info(f"[NewsAPI] {source.name}: {len(articles)} articles")
        except Exception as e:
            logger.error(f"[NewsAPI] {source.name} failed: {e}")

        return articles


# ── JSON Feed Adapter ─────────────────────────────────────────────────────────

class JSONFeedAdapter(BaseSourceAdapter):
    """Fetches from JSON Feed spec (https://www.jsonfeed.org/version/1.1/)."""

    adapter_type = "json_feed"

    async def fetch(self, source: Source, **kwargs) -> List[Dict[str, Any]]:
        articles = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(source.base_url)
                response.raise_for_status()
                data = response.json()

                for item in data.get("items", []):
                    try:
                        title = (item.get("title") or "").strip()
                        url = (item.get("url") or item.get("external_url") or "").strip()
                        if not title or not url:
                            continue

                        content = item.get("content_text") or item.get("content_html") or ""
                        summary = item.get("summary") or ""

                        published_at = datetime.utcnow()
                        date_str = item.get("date_published") or item.get("date_modified")
                        if date_str:
                            try:
                                published_at = datetime.fromisoformat(
                                    date_str.replace("Z", "+00:00")
                                )
                                published_at = published_at.replace(tzinfo=None)
                            except Exception:
                                pass

                        image_url = item.get("image") or item.get("banner_image")

                        normalized = self._normalize(
                            title=title,
                            content=content or summary or title,
                            url=url,
                            published_at=published_at,
                            source=source,
                            image_url=image_url,
                        )
                        if normalized:
                            articles.append(normalized)

                    except Exception as e:
                        logger.warning(f"[JSONFeed] Item normalization failed: {e}")

            logger.info(f"[JSONFeed] {source.name}: {len(articles)} articles")
        except Exception as e:
            logger.error(f"[JSONFeed] {source.name} failed: {e}")

        return articles


# ── Government API Adapter ────────────────────────────────────────────────────

class GovernmentAPIAdapter(BaseSourceAdapter):
    """
    Fetches from government press release APIs.
    Supports generic JSON list endpoints returning objects with
    title/content/date/url fields.
    """

    adapter_type = "government_api"

    # Default field mappings (can be overridden per source)
    FIELD_MAP = {
        "title": ["title", "heading", "subject", "headline"],
        "content": ["content", "body", "description", "text", "abstract"],
        "url": ["url", "link", "href", "press_release_url"],
        "date": ["date", "published_date", "release_date", "created_at", "publishedAt"],
        "image": ["image", "image_url", "thumbnail", "photo"],
    }

    async def fetch(self, source: Source, **kwargs) -> List[Dict[str, Any]]:
        articles = []
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(source.base_url)
                response.raise_for_status()
                data = response.json()

                # Handle both list and dict-wrapped-list responses
                items = data if isinstance(data, list) else data.get("data", data.get("items", data.get("results", [])))
                if not isinstance(items, list):
                    items = []

                for item in items[:100]:
                    try:
                        title = self._extract_field(item, "title")
                        url = self._extract_field(item, "url")
                        if not title or not url:
                            continue

                        content = self._extract_field(item, "content") or title
                        image_url = self._extract_field(item, "image")

                        published_at = datetime.utcnow()
                        date_str = self._extract_field(item, "date")
                        if date_str:
                            try:
                                published_at = datetime.fromisoformat(
                                    str(date_str).replace("Z", "+00:00")
                                )
                                published_at = published_at.replace(tzinfo=None)
                            except Exception:
                                pass

                        normalized = self._normalize(
                            title=title,
                            content=content,
                            url=url,
                            published_at=published_at,
                            source=source,
                            image_url=image_url,
                        )
                        if normalized:
                            articles.append(normalized)

                    except Exception as e:
                        logger.warning(f"[GovAPI] Item normalization failed: {e}")

            logger.info(f"[GovAPI] {source.name}: {len(articles)} articles")
        except Exception as e:
            logger.error(f"[GovAPI] {source.name} failed: {e}")

        return articles

    def _extract_field(self, item: Dict, field_type: str) -> Optional[str]:
        """Try multiple field name variants to find the value."""
        for key in self.FIELD_MAP.get(field_type, []):
            val = item.get(key)
            if val:
                return str(val).strip()
        return None


# ── Adapter Registry ──────────────────────────────────────────────────────────

ADAPTERS = {
    "news": RSSAdapter(),
    "rss": RSSAdapter(),
    "wire": RSSAdapter(),
    "social": RSSAdapter(),
    "newsapi": NewsAPIAdapter(),
    "json_feed": JSONFeedAdapter(),
    "government_api": GovernmentAPIAdapter(),
    "gov_api": GovernmentAPIAdapter(),
}


def get_adapter(source_type: str) -> BaseSourceAdapter:
    """Get the appropriate adapter for a source type."""
    adapter = ADAPTERS.get(source_type)
    if not adapter:
        logger.warning(f"No adapter for source_type={source_type}, falling back to RSS")
        return ADAPTERS["rss"]
    return adapter
