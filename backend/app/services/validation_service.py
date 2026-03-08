"""
Validation Service — enforces thresholds and budget limits before Bedrock calls.
"""
import logging
from dataclasses import dataclass, asdict
from typing import Dict

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    allowed: bool
    reason: str
    score: float
    calls_remaining: int

    def to_dict(self) -> dict:
        return asdict(self)


class ValidationService:
    """Gatekeeps Bedrock calls — enforces score thresholds and session limits."""

    def __init__(self):
        self.score_threshold = settings.score_threshold  # 0.60
        self.max_calls = settings.max_calls_per_session  # 10
        # In-memory session tracking (use DB for production)
        self._session_calls: Dict[str, int] = {}

    def validate_llm_call(self, relation_score: float, session_id: str) -> ValidationResult:
        """
        Check if a Bedrock call is permitted.
        Validates both score threshold and session budget.
        """
        calls_made = self._session_calls.get(session_id, 0)
        calls_remaining = max(0, self.max_calls - calls_made)

        # Check score threshold
        if relation_score < self.score_threshold:
            return ValidationResult(
                allowed=False,
                reason=f"Score {relation_score:.2f} below threshold {self.score_threshold}. "
                       f"Connection too weak for detailed analysis.",
                score=relation_score,
                calls_remaining=calls_remaining,
            )

        # Check session budget
        if calls_remaining <= 0:
            return ValidationResult(
                allowed=False,
                reason=f"Session budget exhausted ({self.max_calls} calls used). "
                       f"Try a new session.",
                score=relation_score,
                calls_remaining=0,
            )

        return ValidationResult(
            allowed=True,
            reason="Validation passed — Bedrock call permitted.",
            score=relation_score,
            calls_remaining=calls_remaining - 1,
        )

    def track_call(self, session_id: str) -> None:
        """Record a Bedrock call for a session."""
        self._session_calls[session_id] = self._session_calls.get(session_id, 0) + 1
        logger.info(
            f"Bedrock call tracked for session {session_id}: "
            f"{self._session_calls[session_id]}/{self.max_calls}"
        )

    def get_call_count(self, session_id: str) -> int:
        """Get the number of Bedrock calls made in a session."""
        return self._session_calls.get(session_id, 0)

    def reset_session(self, session_id: str) -> None:
        """Reset call count for a session."""
        self._session_calls.pop(session_id, None)
