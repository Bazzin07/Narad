"""
LLM Rate Limiter / Circuit Breaker — prevents runaway LLM costs.

Three-layer protection:
1. Per-minute rate limit (default: 30 calls/min)
2. Per-hour rate limit (default: 200 calls/hr)
3. Total budget cap (configurable)

If any limit is exceeded, the call is BLOCKED and the system falls back
to deterministic (non-LLM) processing. This prevents infinite loops,
retry storms, and credit exhaustion.
"""
import logging
import time
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class LLMRateLimitExceeded(Exception):
    """Raised when LLM rate limit is exceeded."""
    pass


class LLMCircuitBreaker:
    """Thread-safe rate limiter for LLM API calls."""

    def __init__(
        self,
        max_per_minute: int = 30,
        max_per_hour: int = 200,
        max_total: Optional[int] = None,
    ):
        self._max_per_minute = max_per_minute
        self._max_per_hour = max_per_hour
        self._max_total = max_total
        self._calls_minute: list[float] = []
        self._calls_hour: list[float] = []
        self._total_calls = 0
        self._total_blocked = 0
        self._lock = threading.Lock()
        self._tripped = False  # emergency stop

    def trip(self):
        """Emergency stop — block ALL future calls."""
        self._tripped = True
        logger.critical("🚨 LLM Circuit Breaker TRIPPED — all calls blocked")

    def reset(self):
        """Reset the circuit breaker."""
        self._tripped = False
        with self._lock:
            self._calls_minute.clear()
            self._calls_hour.clear()
        logger.info("Circuit breaker reset")

    def check_and_record(self) -> bool:
        """
        Check if a call is allowed, and record it.
        Returns True if allowed, False if rate limit exceeded.
        """
        if self._tripped:
            self._total_blocked += 1
            return False

        now = time.time()
        with self._lock:
            # Prune expired entries
            self._calls_minute = [t for t in self._calls_minute if now - t < 60]
            self._calls_hour = [t for t in self._calls_hour if now - t < 3600]

            # Check limits
            if len(self._calls_minute) >= self._max_per_minute:
                self._total_blocked += 1
                logger.warning(
                    f"LLM rate limit (minute) exceeded: "
                    f"{len(self._calls_minute)}/{self._max_per_minute}"
                )
                return False

            if len(self._calls_hour) >= self._max_per_hour:
                self._total_blocked += 1
                logger.warning(
                    f"LLM rate limit (hour) exceeded: "
                    f"{len(self._calls_hour)}/{self._max_per_hour}"
                )
                return False

            if self._max_total and self._total_calls >= self._max_total:
                self._total_blocked += 1
                logger.warning(
                    f"LLM total budget limit exceeded: "
                    f"{self._total_calls}/{self._max_total}"
                )
                return False

            # All checks passed — record the call
            self._calls_minute.append(now)
            self._calls_hour.append(now)
            self._total_calls += 1
            return True

    @property
    def stats(self) -> dict:
        """Current rate limiter statistics."""
        now = time.time()
        with self._lock:
            minute_calls = len([t for t in self._calls_minute if now - t < 60])
            hour_calls = len([t for t in self._calls_hour if now - t < 3600])

        return {
            "tripped": self._tripped,
            "calls_this_minute": minute_calls,
            "calls_this_hour": hour_calls,
            "total_calls": self._total_calls,
            "total_blocked": self._total_blocked,
            "limits": {
                "per_minute": self._max_per_minute,
                "per_hour": self._max_per_hour,
                "total": self._max_total,
            },
        }


# Global singleton
llm_rate_limiter = LLMCircuitBreaker(
    max_per_minute=30,
    max_per_hour=200,
    max_total=10000,  # safety cap
)
