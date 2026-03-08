"""
Sentiment Service — rule-based polarity scoring for news articles.

Uses a lightweight keyword-based approach (no external model needed):
  - Negative words: conflict, war, death, crisis, attack, etc.
  - Positive words: agreement, growth, peace, success, etc.
  - Weighted scoring with title emphasis

Returns a value in [-1.0, 1.0] where:
  -1.0 = very negative
   0.0 = neutral
  +1.0 = very positive
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Sentiment Lexicons ────────────────────────────────────────────────────────

NEGATIVE_WORDS = {
    # Violence / Conflict
    "war": 3, "attack": 3, "killed": 3, "death": 3, "bomb": 3, "bombing": 3,
    "airstrike": 3, "missile": 3, "conflict": 2, "violence": 3, "massacre": 3,
    "shooting": 3, "terror": 3, "terrorist": 3, "hostage": 3, "casualties": 3,
    "wounded": 2, "destroyed": 2, "explosion": 3, "shelling": 2, "invasion": 3,
    # Crisis / Disaster
    "crisis": 2, "flood": 2, "earthquake": 2, "cyclone": 2, "disaster": 2,
    "drought": 2, "famine": 2, "collapse": 2, "recession": 2, "pandemic": 2,
    "epidemic": 2, "outbreak": 2, "emergency": 2,
    # Negative politics
    "corruption": 2, "scandal": 2, "protest": 1, "arrested": 2, "detained": 2,
    "accused": 1, "banned": 1, "sanctions": 2, "coup": 3, "authoritarian": 2,
    "crackdown": 2, "repression": 2, "censorship": 2,
    # Economic negative
    "inflation": 1, "unemployment": 2, "debt": 1, "bankruptcy": 2, "loss": 1,
    "decline": 1, "crash": 2, "plunge": 2, "slump": 2,
    # Hindi
    "yuddh": 3, "hamla": 3, "aatankvad": 3, "baadh": 2, "bhukamp": 2,
    "mehngai": 2, "beroozgaari": 2, "mahamari": 2,
}

POSITIVE_WORDS = {
    # Peace / Diplomacy
    "peace": 3, "agreement": 2, "treaty": 2, "ceasefire": 2, "cooperation": 2,
    "summit": 1, "alliance": 1, "diplomatic": 1, "negotiation": 1, "resolved": 2,
    "reconciliation": 2, "normalization": 2,
    # Growth / Success
    "growth": 2, "success": 2, "achievement": 2, "record": 1, "milestone": 2,
    "breakthrough": 2, "innovation": 2, "progress": 1, "development": 1,
    "improvement": 1, "recovery": 2, "surge": 1, "rally": 1,
    # Positive events
    "celebrate": 2, "celebration": 2, "festival": 1, "launched": 1, "elected": 1,
    "awarded": 2, "rescued": 2, "saved": 1, "victory": 2, "win": 1, "won": 1,
    # Economic positive
    "investment": 1, "profit": 1, "boom": 2, "flourish": 2, "thriving": 2,
    # Hindi
    "shanti": 3, "samjhota": 2, "vikas": 2, "safalta": 2, "utsav": 1,
    "jeet": 2,
}

# Pre-compile patterns
_NEG_PATTERNS = [
    (re.compile(r'\b' + re.escape(w) + r'\b', re.IGNORECASE), weight)
    for w, weight in NEGATIVE_WORDS.items()
]
_POS_PATTERNS = [
    (re.compile(r'\b' + re.escape(w) + r'\b', re.IGNORECASE), weight)
    for w, weight in POSITIVE_WORDS.items()
]


def compute_sentiment(title: str, content: str) -> float:
    """
    Compute sentiment score for an article.
    Returns float in [-1.0, 1.0].
    """
    # Title weighted 3x
    text = f"{title} {title} {title} {content[:2000]}"

    pos_score = 0
    neg_score = 0

    for pattern, weight in _POS_PATTERNS:
        matches = pattern.findall(text)
        pos_score += len(matches) * weight

    for pattern, weight in _NEG_PATTERNS:
        matches = pattern.findall(text)
        neg_score += len(matches) * weight

    total = pos_score + neg_score
    if total == 0:
        return 0.0

    # Range: -1.0 to 1.0
    raw = (pos_score - neg_score) / total
    return round(max(-1.0, min(1.0, raw)), 3)


def sentiment_label(score: float) -> str:
    """Convert numeric sentiment to label."""
    if score >= 0.3:
        return "Positive"
    elif score <= -0.3:
        return "Negative"
    return "Neutral"
