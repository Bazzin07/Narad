"""
Ingestion Service — fetches from registered sources, normalizes,
deduplicates (URL + content hash), detects language, and stores.

No LLM calls. No embeddings. Pure data collection.
"""
import re
import hashlib
import logging
import asyncio
from datetime import datetime
from time import mktime
from typing import List, Dict, Any, Optional

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, Source
from app.services.storage_service import get_storage
from app.config import settings

logger = logging.getLogger(__name__)

# Lazy-load langdetect
_langdetect = None


def _detect_language(text: str) -> str:
    """Detect language of text. Returns ISO 639-1 code (en, hi, fr, etc.)."""
    global _langdetect
    if _langdetect is None:
        try:
            from langdetect import detect
            _langdetect = detect
        except ImportError:
            logger.warning("langdetect not installed — defaulting to 'en'")
            return settings.default_language

    try:
        if len(text.strip()) < 20:
            return settings.default_language
        return _langdetect(text)
    except Exception:
        return settings.default_language


def _content_hash(title: str, content: str) -> str:
    """Generate SHA-256 hash of title + first 300 chars of content."""
    raw = f"{title.strip().lower()}|{content[:300].strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sanitize_content(text: str) -> str:
    """
    Strip garbage from article content:
    - YouTube descriptions (subscribe, follow, social links)
    - Hashtag blocks
    - Social media prompts
    - Channel marketing text
    - Repeated dashes/separators
    """
    if not text:
        return text

    # Split into lines for line-level filtering
    lines = text.split('\n')
    clean_lines = []

    skip_patterns = [
        # Social media & subscription prompts
        re.compile(r'(subscribe|follow\s+us|click\s+here\s+to)', re.IGNORECASE),
        re.compile(r'(instagram|facebook|twitter|youtube)\.com/', re.IGNORECASE),
        re.compile(r'https?://\S*(youtube|fb|twitter|instagram|bit\.ly)\S*', re.IGNORECASE),
        # YouTube boilerplate
        re.compile(r'(watch\s+live|watch\s+abp|live\s+tv|24\s*\*\s*7)', re.IGNORECASE),
        re.compile(r'(is\s+a\s+(news|popular)\s+(hub|channel))', re.IGNORECASE),
        re.compile(r'(made\s+its\s+debut|re-branded|vision\s+of\s+the\s+channel)', re.IGNORECASE),
        re.compile(r'(aapko\s+rakhe|cutting-edge\s+formats|state-of-the-art\s+newsrooms)', re.IGNORECASE),
        re.compile(r'(ABP\s+News\s+is\s+)', re.IGNORECASE),
        re.compile(r'(sub_confirmation|www\.youtube\.com/@)', re.IGNORECASE),
        # Marketing fluff
        re.compile(r'(get\s+the\s+latest|comprehensive\s+up-to-date)', re.IGNORECASE),
        re.compile(r'(breaking\s+stories|current\s+affairs\s+news)', re.IGNORECASE),
    ]

    for line in lines:
        stripped = line.strip()

        # Skip empty lines and separator lines
        if not stripped or re.match(r'^[-=_]{5,}$', stripped):
            continue

        # Skip lines that are mostly hashtags
        hashtag_count = len(re.findall(r'#\w+', stripped))
        word_count = len(stripped.split())
        if word_count > 0 and hashtag_count / word_count > 0.4:
            continue

        # Skip lines matching any garbage pattern
        if any(p.search(stripped) for p in skip_patterns):
            continue

        # Skip very short URL-only lines
        if re.match(r'^https?://\S+$', stripped):
            continue

        clean_lines.append(stripped)

    result = ' '.join(clean_lines)

    # Remove inline hashtag clusters (4+ hashtags in a row)
    result = re.sub(r'(#\w+\s*){4,}', '', result)

    # Remove remaining URLs
    result = re.sub(r'https?://\S+', '', result)

    # Reddit-specific cleanup
    result = re.sub(r'submitted\s+by\s+/?u/\S+', '', result, flags=re.IGNORECASE)
    result = re.sub(r'/u/\S+', '', result, flags=re.IGNORECASE)
    result = re.sub(r'\[link\]', '', result, flags=re.IGNORECASE)
    result = re.sub(r'\[comments?\]', '', result, flags=re.IGNORECASE)
    result = re.sub(r'&amp;?#\d+;', ' ', result)  # HTML entities like &#32;
    result = re.sub(r'&\w+;', ' ', result)  # &amp; &gt; etc.

    # General promotional text
    result = re.sub(r'(download\s+(our\s+)?app|available\s+on\s+(app\s+store|google\s+play))', '', result, flags=re.IGNORECASE)
    result = re.sub(r'(for\s+more\s+(news|updates|stories|info))', '', result, flags=re.IGNORECASE)

    # Clean up whitespace
    result = re.sub(r'\s{2,}', ' ', result).strip()

    return result


# ── Full Content Scraping ─────────────────────────────────────────────────────

_trafilatura = None


def _extract_full_content(html: str, url: str) -> str:
    """Extract full article text from HTML using trafilatura."""
    global _trafilatura
    if _trafilatura is None:
        try:
            import trafilatura
            _trafilatura = trafilatura
        except ImportError:
            logger.warning("trafilatura not installed — skipping full content extraction")
            return ""
    try:
        text = _trafilatura.extract(html, url=url, include_comments=False,
                                     include_tables=False, deduplicate=True) or ""
        return text.strip()
    except Exception as e:
        logger.debug(f"trafilatura extraction failed for {url}: {e}")
        return ""


async def _scrape_article_content(url: str, timeout: float = 8.0) -> str:
    """Fetch and extract full article content from a URL."""
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NaradBot/2.0)"}
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
            # Run trafilatura in thread to not block async loop
            loop = asyncio.get_event_loop()
            full_text = await loop.run_in_executor(None, _extract_full_content, html, url)
            return full_text
    except Exception as e:
        logger.debug(f"Failed to scrape {url}: {e}")
        return ""


# ── Default Source Seeds ──────────────────────────────────────────────────────
# Import from the central sources registry — only feed sources (no YT/Reddit)
from app.sources import FEED_SOURCES

DEFAULT_SOURCES = [
    {
        "name": s["name"],
        "base_url": s["base_url"],
        "source_type": s["source_type"],
        "language": s["language"],
        "credibility_weight": s["credibility_weight"],
        "source_region": "global" if s.get("region") == "international" else "india",
    }
    for s in FEED_SOURCES
]


class IngestionService:
    """Collects and normalizes news from registered sources."""

    def __init__(self):
        self.storage = get_storage()

    # ── Source Registry ───────────────────────────────────────────────────────

    async def seed_default_sources(self, db: AsyncSession) -> int:
        """Ensure all DEFAULT_SOURCES exist in the registry (upsert by name)."""
        # Get existing source names
        result = await db.execute(select(Source.name))
        existing_names = {row[0] for row in result.fetchall()}

        count = 0
        for src in DEFAULT_SOURCES:
            if src["name"] not in existing_names:
                source = Source(**src)
                db.add(source)
                count += 1

        if count:
            await db.flush()
            logger.info(f"Registered {count} new sources")
        return count

    async def get_active_sources(self, db: AsyncSession) -> List[Source]:
        """Get all active sources from the registry."""
        result = await db.execute(
            select(Source).where(Source.active == True)  # noqa: E712
        )
        return list(result.scalars().all())

    # ── RSS Feeds ─────────────────────────────────────────────────────────────

    async def fetch_from_rss(self, feed_url: str, source: Optional[Source] = None) -> List[Dict[str, Any]]:
        """Fetch articles from a single RSS feed. Returns normalized dicts."""
        articles = []
        try:
            feed = feedparser.parse(feed_url)
            source_name = source.name if source else feed.feed.get("title", feed_url)

            for entry in feed.entries:
                try:
                    article = self._normalize_rss_entry(entry, source_name, feed_url, source)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to normalize RSS entry from {feed_url}: {e}")
                    continue

            logger.info(f"Fetched {len(articles)} articles from RSS: {source_name}")
        except Exception as e:
            logger.error(f"Failed to fetch RSS feed {feed_url}: {e}")

        return articles

    def _normalize_rss_entry(
        self, entry: Any, source_name: str, feed_url: str, source: Optional[Source] = None
    ) -> Optional[Dict[str, Any]]:
        """Convert an RSS entry to our standard article format."""
        title = entry.get("title", "").strip()
        if not title:
            return None

        # Extract content — handles news RSS, YouTube Atom, Reddit feeds
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.get("summary", "")
        elif hasattr(entry, "description"):
            content = entry.get("description", "")

        # YouTube Atom feeds: content is in media_description
        if not content or len(content) < 30:
            if hasattr(entry, "media_description"):
                content = entry.media_description or ""

        # Strip HTML tags
        content = re.sub(r"<[^>]+>", " ", content).strip()
        content = re.sub(r"\s+", " ", content)

        # Sanitize: remove YouTube boilerplate, hashtags, social links
        content = _sanitize_content(content)

        if not content or len(content) < 50:
            content = title

        # Parse publish date
        published_at = datetime.utcnow()
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_at = datetime.fromtimestamp(mktime(entry.published_parsed))
            except Exception:
                pass

        link = entry.get("link", "")
        if not link:
            return None

        # Detect language
        lang = _detect_language(f"{title}. {content}")

        # Content hash for dedup
        chash = _content_hash(title, content)

        # Topic classification
        from app.services.topic_classifier import get_primary_topic
        topic = get_primary_topic(title, content, lang)

        # Image extraction — check media:content, media:thumbnail, enclosures
        image_url = self._extract_image(entry)

        return {
            "title": title,
            "content": content,
            "summary": content[:500] if len(content) > 500 else content,
            "source": source_name,
            "source_id": source.id if source else None,
            "source_type": source.source_type if source else "news",
            "url": link,
            "published_at": published_at,
            "language": lang if source is None else (source.language or lang),
            "credibility_weight": source.credibility_weight if source else 1.0,
            "content_hash": chash,
            "topic": topic,
            "image_url": image_url,
            "source_region": source.source_region if source else "global",
        }

    def _extract_image(self, entry) -> Optional[str]:
        """Extract image URL from RSS entry. Checks media:content, media:thumbnail, enclosures, img tags."""
        # 1. media:content - accept explicit image type OR URL with image extension
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if isinstance(media, dict) and media.get('url'):
                    url = media['url']
                    mtype = media.get('type', '')
                    if mtype.startswith('image') or not mtype or re.search(r'\.(jpe?g|png|webp|gif)(\?|$)', url, re.IGNORECASE):
                        return url

        # 2. media:thumbnail
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            for thumb in entry.media_thumbnail:
                if isinstance(thumb, dict) and thumb.get('url'):
                    return thumb['url']

        # 3. Enclosures
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures:
                if isinstance(enc, dict) and enc.get('href'):
                    etype = enc.get('type', '')
                    href = enc['href']
                    if etype.startswith('image') or not etype or re.search(r'\.(jpe?g|png|webp|gif)(\?|$)', href, re.IGNORECASE):
                        return href

        # 4. Extract first <img> from HTML (skip tracking pixels/spacers)
        raw = entry.get('summary', '') or ''
        if hasattr(entry, 'content') and entry.content:
            raw = entry.content[0].get('value', '') or raw
        img_match = re.search(r'<img[^>]+src=["\']([^"\'>]+)["\']', raw)
        if img_match:
            candidate = img_match.group(1)
            if not re.search(r'(pixel|tracker|1x1|spacer|blank)', candidate, re.IGNORECASE):
                return candidate

        return None

    # ── News API ──────────────────────────────────────────────────────────────

    async def fetch_from_api(self, category: str = "general", country: str = "us") -> List[Dict[str, Any]]:
        """Fetch articles from NewsAPI. Returns normalized dicts."""
        if not settings.news_api_key:
            logger.info("No NEWS_API_KEY configured — skipping API fetch")
            return []

        articles = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {
                    "category": category,
                    "country": country,
                    "apiKey": settings.news_api_key,
                    "pageSize": 50,
                }
                response = await client.get(settings.news_api_url, params=params)
                response.raise_for_status()
                data = response.json()

                for item in data.get("articles", []):
                    try:
                        article = self._normalize_api_article(item)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.warning(f"Failed to normalize API article: {e}")

            logger.info(f"Fetched {len(articles)} articles from NewsAPI")
        except Exception as e:
            logger.error(f"Failed to fetch from NewsAPI: {e}")

        return articles

    def _normalize_api_article(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a NewsAPI article to our standard format."""
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        if not title or not url:
            return None

        content = item.get("content") or item.get("description") or title
        content = re.sub(r"\[\+\d+ chars\]$", "", content).strip()

        source_name = "Unknown"
        if isinstance(item.get("source"), dict):
            source_name = item["source"].get("name", "Unknown")

        published_at = datetime.utcnow()
        if item.get("publishedAt"):
            try:
                published_at = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
                published_at = published_at.replace(tzinfo=None)
            except Exception:
                pass

        lang = _detect_language(f"{title}. {content}")
        chash = _content_hash(title, content)

        # Topic classification
        from app.services.topic_classifier import get_primary_topic
        topic = get_primary_topic(title, content, lang)

        # Image from NewsAPI
        image_url = item.get("urlToImage") or None

        return {
            "title": title,
            "content": content,
            "summary": content[:500] if len(content) > 500 else content,
            "source": source_name,
            "source_id": None,
            "source_type": "news",
            "url": url,
            "published_at": published_at,
            "language": lang,
            "credibility_weight": 0.8,  # API sources slightly lower
            "content_hash": chash,
            "topic": topic,
            "image_url": image_url,
        }

    # ── Deduplication ─────────────────────────────────────────────────────────

    async def is_duplicate(self, url: str, content_hash: str, db: AsyncSession) -> bool:
        """
        Two-tier deduplication:
         1. URL match (exact dupe)
         2. Content hash match (same article, different URL)
        """
        # URL check
        result = await db.execute(select(Article.id).where(Article.url == url).limit(1))
        if result.scalar_one_or_none() is not None:
            return True

        # Content hash check
        if content_hash:
            result = await db.execute(
                select(Article.id).where(Article.content_hash == content_hash).limit(1)
            )
            if result.scalar_one_or_none() is not None:
                return True

        return False

    # ── Storage ───────────────────────────────────────────────────────────────

    async def store_article(self, article_data: Dict[str, Any], db: AsyncSession) -> Optional[Article]:
        """Store a normalized article. Returns Article ORM object, or None if duplicate.
        
        v2: Attempts full content scraping via trafilatura when RSS content is short.
        """
        url = article_data["url"]
        content_hash = article_data.get("content_hash", "")

        if await self.is_duplicate(url, content_hash, db):
            return None

        # Attempt full content scraping if RSS content is too short
        content = article_data["content"]
        if len(content) < 300 and url:
            try:
                full_text = await _scrape_article_content(url, timeout=8.0)
                if full_text and len(full_text) > len(content):
                    content = _sanitize_content(full_text)
                    article_data["content"] = content
                    article_data["summary"] = content[:500] if len(content) > 500 else content
                    # Re-hash with full content
                    content_hash = _content_hash(article_data["title"], content)
                    article_data["content_hash"] = content_hash
                    logger.debug(f"Scraped full content ({len(content)} chars) for: {article_data['title'][:50]}")
            except Exception as e:
                logger.debug(f"Content scraping failed for {url}: {e}")

        # Generate storage key
        url_hash = hashlib.md5(url.encode()).hexdigest()
        date_prefix = article_data["published_at"].strftime("%Y/%m/%d")
        s3_key = f"articles/{date_prefix}/{url_hash}.json"

        try:
            self.storage.store(s3_key, article_data)
        except Exception as e:
            logger.error(f"Failed to store raw article {url}: {e}")
            s3_key = ""

        # Classify geographic scope
        from app.services.geo_scope_classifier import classify_geo_scope, extract_state
        geo_scope = classify_geo_scope(
            title=article_data["title"],
            content=content,
            source_region=article_data.get("source_region"),
            language=article_data.get("language"),
        )

        # Extract Indian state (if applicable)
        article_state = extract_state(article_data["title"], content) if geo_scope in ("india", "mixed") else None

        # Compute sentiment score
        from app.services.sentiment_service import compute_sentiment
        sentiment = compute_sentiment(article_data["title"], content)

        article = Article(
            title=article_data["title"],
            content=content,
            summary=article_data.get("summary", ""),
            source=article_data["source"],
            source_id=article_data.get("source_id"),
            url=url,
            published_at=article_data["published_at"],
            s3_key=s3_key,
            processed=0,
            language=article_data.get("language", settings.default_language),
            credibility_weight=article_data.get("credibility_weight", 1.0),
            content_hash=content_hash,
            topic=article_data.get("topic", "general"),
            image_url=article_data.get("image_url"),
            geographic_scope=geo_scope,
            state=article_state,
            sentiment_score=sentiment,
        )
        db.add(article)
        await db.flush()
        logger.info(f"Stored [{article.language}|{geo_scope}] {article.title[:55]}... [{article.id}]")
        return article

    # ── Full Ingestion Run ────────────────────────────────────────────────────

    async def run_ingestion(self, db: AsyncSession) -> Dict[str, Any]:
        """Execute a full ingestion cycle from all active sources with health monitoring."""
        all_articles = []
        errors = []
        source_stats: Dict[str, int] = {}  # source_id -> articles fetched

        # Seed defaults if needed
        await self.seed_default_sources(db)

        # Fetch from registered sources
        active_sources = await self.get_active_sources(db)

        if active_sources:
            # Concurrent fetch in batches of 10 to avoid overwhelming the network
            batch_size = 10
            for i in range(0, len(active_sources), batch_size):
                batch = active_sources[i:i + batch_size]
                tasks = []
                for source in batch:
                    tasks.append(self._fetch_with_health(source, db))
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for source, result in zip(batch, results):
                    if isinstance(result, Exception):
                        errors.append(f"Source {source.name}: {result}")
                    elif isinstance(result, list):
                        source_stats[source.id] = len(result)
                        all_articles.extend(result)
        else:
            # Fallback to config-based RSS feeds
            for feed_url in settings.rss_feed_list:
                try:
                    articles = await self.fetch_from_rss(feed_url)
                    all_articles.extend(articles)
                except Exception as e:
                    error_msg = f"RSS feed {feed_url}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

        # Fetch from News API
        try:
            api_articles = await self.fetch_from_api()
            all_articles.extend(api_articles)
        except Exception as e:
            error_msg = f"NewsAPI: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

        # Store articles
        stored = 0
        skipped = 0
        for article_data in all_articles:
            try:
                result = await self.store_article(article_data, db)
                if result:
                    stored += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Failed to store article: {e}")
                errors.append(str(e))

        await db.commit()

        summary = {
            "articles_fetched": len(all_articles),
            "articles_stored": stored,
            "articles_skipped": skipped,
            "sources_used": len(active_sources) if active_sources else len(settings.rss_feed_list),
            "errors": errors,
        }
        logger.info(f"Ingestion complete: {summary}")
        return summary

    async def _fetch_with_health(self, source: Source, db: AsyncSession) -> List[Dict[str, Any]]:
        """Fetch from a single source and update its health status.
        
        Routes to the appropriate adapter based on source_type.
        """
        now = datetime.utcnow()
        try:
            # Route to appropriate adapter based on source_type
            source_type = (source.source_type or "news").lower()
            if source_type in ("news", "wire", "social", "rss"):
                # Use existing RSS fetch for backward compatibility
                articles = await self.fetch_from_rss(source.base_url, source=source)
            else:
                # Use modular adapter system for non-RSS sources
                from app.services.source_adapters import get_adapter
                adapter = get_adapter(source_type)
                articles = await adapter.fetch(source)

            # Update health — success
            source.last_fetched_at = now
            source.total_fetches = (source.total_fetches or 0) + 1
            if articles:
                source.last_success_at = now
                source.consecutive_failures = 0
                source.total_articles_fetched = (source.total_articles_fetched or 0) + len(articles)
            else:
                # No articles — could be a slow period, increment failures gently
                source.consecutive_failures = (source.consecutive_failures or 0) + 1

            # Auto-disable after 10 consecutive failures
            if (source.consecutive_failures or 0) >= 10:
                source.active = False
                logger.warning(f"⚠️ Auto-disabled source '{source.name}' after {source.consecutive_failures} consecutive failures")

            return articles
        except Exception as e:
            # Update health — failure
            source.last_fetched_at = now
            source.total_fetches = (source.total_fetches or 0) + 1
            source.consecutive_failures = (source.consecutive_failures or 0) + 1

            if (source.consecutive_failures or 0) >= 10:
                source.active = False
                logger.warning(f"⚠️ Auto-disabled source '{source.name}' after {source.consecutive_failures} consecutive failures")

            logger.error(f"Source {source.name}: {e}")
            raise

    async def get_source_health(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get health status for all sources (for dashboard API)."""
        from sqlalchemy import func
        result = await db.execute(
            select(Source).order_by(Source.active.desc(), Source.consecutive_failures.desc())
        )
        sources = result.scalars().all()

        health_data = []
        for s in sources:
            # Count articles from this source in last 24h
            recent_cutoff = datetime.utcnow()
            try:
                from datetime import timedelta
                recent_result = await db.execute(
                    select(func.count(Article.id))
                    .where(Article.source_id == s.id)
                    .where(Article.created_at >= recent_cutoff - timedelta(hours=24))
                )
                recent_count = recent_result.scalar() or 0
            except Exception:
                recent_count = 0

            # Determine health status
            if not s.active:
                status = "disabled"
            elif (s.consecutive_failures or 0) >= 5:
                status = "failing"
            elif (s.consecutive_failures or 0) >= 2:
                status = "degraded"
            elif s.last_success_at and (datetime.utcnow() - s.last_success_at).total_seconds() < 7200:
                status = "healthy"
            elif s.last_fetched_at:
                status = "stale"
            else:
                status = "unknown"

            health_data.append({
                "id": s.id,
                "name": s.name,
                "base_url": s.base_url,
                "source_type": s.source_type,
                "language": s.language,
                "source_region": s.source_region,
                "active": s.active,
                "status": status,
                "last_fetched_at": str(s.last_fetched_at) if s.last_fetched_at else None,
                "last_success_at": str(s.last_success_at) if s.last_success_at else None,
                "consecutive_failures": s.consecutive_failures or 0,
                "total_fetches": s.total_fetches or 0,
                "total_articles_fetched": s.total_articles_fetched or 0,
                "articles_last_24h": recent_count,
            })

        return health_data

