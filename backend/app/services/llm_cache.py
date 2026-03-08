"""
LLM Semantic Cache — prevents duplicate LLM calls for identical inputs.

Uses in-memory LRU cache with SHA-256 content hashing. If the same
article pair or prompt is evaluated twice, the second call costs $0.

This is the first layer of the cost-control infrastructure.
"""
import hashlib
import logging
import time
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger(__name__)


class LLMCache:
    """In-memory LRU cache for LLM responses with TTL support."""

    def __init__(self, max_size: int = 5000, default_ttl: int = 3600):
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl  # seconds
        self._hits = 0
        self._misses = 0

    @staticmethod
    def make_key(*parts: str) -> str:
        """Create cache key from arbitrary string parts."""
        combined = "|".join(str(p) for p in parts)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def get(self, key: str) -> Optional[str]:
        """Get cached response. Returns None on miss or expiry."""
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None

        # Check TTL
        if time.time() > entry["expires_at"]:
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        return entry["value"]

    def set(self, key: str, value: str, ttl: Optional[int] = None):
        """Store response in cache."""
        if key in self._cache:
            self._cache.move_to_end(key)
        elif len(self._cache) >= self._max_size:
            # Evict oldest entry
            evicted_key, _ = self._cache.popitem(last=False)
            logger.debug(f"LLM cache evicted key: {evicted_key[:8]}...")

        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + (ttl or self._default_ttl),
        }

    def invalidate(self, key: str):
        """Remove a specific cache entry."""
        self._cache.pop(key, None)

    def clear(self):
        """Clear entire cache."""
        self._cache.clear()
        logger.info("LLM cache cleared")

    @property
    def stats(self) -> dict:
        """Cache hit/miss statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{(self._hits / total * 100):.1f}%" if total > 0 else "0%",
        }


# Global singleton
llm_cache = LLMCache(max_size=5000, default_ttl=3600)
