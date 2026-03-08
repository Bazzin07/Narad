"""
Redis Cache Service for Narad.

Provides transparent caching for frequently accessed data:
- Article details (TTL: 10 min)
- News feed results (TTL: 2 min)
- Causal chain results (TTL: 30 min)
- LLM analysis outputs (TTL: 1 hour)
- Probe results (TTL: 30 min)

Gracefully degrades if Redis is unavailable — all operations become no-ops.
"""
import json
import hashlib
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# TTL constants (seconds)
TTL_FEED = 120          # 2 minutes for feed queries
TTL_ARTICLE = 600       # 10 minutes for article details
TTL_CHAINS = 1800       # 30 minutes for chain results
TTL_ANALYSIS = 3600     # 1 hour for LLM-generated analysis
TTL_PROBE = 1800        # 30 minutes for probe results

_redis_client = None
_redis_available = None


def _get_redis():
    """Lazy-initialize Redis connection. Returns None if unavailable."""
    global _redis_client, _redis_available
    
    if _redis_available is False:
        return None
    
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.Redis(
                host="localhost",
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            _redis_client.ping()
            _redis_available = True
            logger.info("✅ Redis cache connected")
        except Exception as e:
            logger.info(f"Redis not available — caching disabled: {e}")
            _redis_available = False
            _redis_client = None
            return None
    
    return _redis_client


def cache_get(key: str) -> Optional[Any]:
    """Get a value from cache. Returns None on miss or error."""
    r = _get_redis()
    if r is None:
        return None
    try:
        data = r.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.debug(f"Cache get error for {key}: {e}")
    return None


def cache_set(key: str, value: Any, ttl: int = TTL_ARTICLE) -> bool:
    """Set a value in cache with TTL. Returns True on success."""
    r = _get_redis()
    if r is None:
        return False
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.debug(f"Cache set error for {key}: {e}")
    return False


def cache_delete(key: str) -> bool:
    """Delete a cache key. Returns True on success."""
    r = _get_redis()
    if r is None:
        return False
    try:
        r.delete(key)
        return True
    except Exception as e:
        logger.debug(f"Cache delete error for {key}: {e}")
    return False


def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count deleted."""
    r = _get_redis()
    if r is None:
        return 0
    try:
        keys = r.keys(pattern)
        if keys:
            return r.delete(*keys)
    except Exception as e:
        logger.debug(f"Cache delete pattern error for {pattern}: {e}")
    return 0


# ── Key builders ──────────────────────────────────────────────────────────────

def feed_key(region: str = "all", language: str = "all", offset: int = 0, limit: int = 20) -> str:
    return f"feed:{region}:{language}:{offset}:{limit}"

def article_key(article_id: str) -> str:
    return f"article:{article_id}"

def chains_key(article_id: str) -> str:
    return f"chains:{article_id}"

def analysis_key(article_id: str) -> str:
    return f"analysis:{article_id}"

def probe_key(text: str) -> str:
    text_hash = hashlib.md5(text.encode()).hexdigest()
    return f"probe:{text_hash}"
