"""
Topic Classifier Service — assigns explicit topic tags to articles.

Uses a keyword-based approach with weighted domain dictionaries, optimised for
Indian and global news relevant to the Narad project.

Topics:
  military, politics, economy, diplomacy, terrorism, energy,
  technology, health, environment, sports, social
"""
import re
import logging
from typing import List, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


# ── Domain Keyword Dictionaries ───────────────────────────────────────────────
# Each keyword has a weight; higher = stronger signal.
# Includes English AND transliterated Hindi/Indian language keywords.

TOPIC_KEYWORDS = {
    "military": {
        # English
        "airstrike": 3, "missile": 3, "bombing": 3, "military": 2, "troops": 2,
        "war": 2, "strike": 2, "fighter jets": 3, "artillery": 2, "drone": 2,
        "combat": 2, "defense": 1, "defence": 1, "army": 2, "navy": 2,
        "air force": 2, "nuclear": 2, "warship": 2, "ceasefire": 2,
        "invasion": 3, "occupation": 2, "weapons": 2, "ammunition": 2,
        "soldier": 2, "casualties": 2, "killed in action": 3, "shelling": 2,
        "ballistic": 3, "retaliatory": 2, "surgical strike": 3,
        # Hindi (transliterated)
        "havaai hamla": 3, "sena": 2, "yuddh": 2, "fauj": 2, "hamla": 2,
        "missile": 3, "sainik": 2, "raksha": 1, "hatiyaar": 2,
        "paramanu": 2, "saiiya prtikriyaa": 2,
    },
    "politics": {
        "election": 3, "parliament": 2, "government": 1, "minister": 2,
        "prime minister": 3, "president": 2, "opposition": 2, "legislation": 2,
        "bill passed": 3, "vote": 2, "referendum": 3, "coalition": 2,
        "political": 1, "congress": 2, "bjp": 2, "modi": 2, "rahul gandhi": 3,
        "lok sabha": 3, "rajya sabha": 3, "assembly": 2, "governor": 2,
        "democracy": 1, "authoritarian": 2, "coup": 3, "protest": 2,
        "rally": 2, "manifesto": 2, "policy": 1,
        # Hindi
        "chunav": 3, "sarkaar": 2, "mantri": 2, "pradhan mantri": 3,
        "virodhi": 2, "raajneeti": 2, "sangsad": 2, "vidhansabha": 2,
        "loksabha": 3, "rajyasabha": 3, "netaa": 2,
    },
    "economy": {
        "gdp": 3, "inflation": 3, "market": 2, "stocks": 2, "recession": 3,
        "trade": 2, "tariff": 2, "exports": 2, "imports": 2, "debt": 2,
        "budget": 2, "fiscal": 2, "monetary": 2, "rbi": 3, "reserve bank": 3,
        "interest rate": 3, "unemployment": 2, "jobs": 1, "rupee": 2,
        "dollar": 1, "sensex": 3, "nifty": 3, "share price": 2,
        "investment": 2, "fdi": 3, "subsidies": 2, "gst": 2, "tax": 2,
        "revenue": 1, "economic": 2, "central bank": 2, "imf": 2,
        # Hindi
        "arthvyavastha": 3, "mehngai": 3, "bazaar": 2, "vyapaar": 2,
        "karobar": 2, "naukri": 1, "beroozgaari": 2, "bajat": 2,
        "mudrasfiti": 3, "niveesh": 2,
    },
    "diplomacy": {
        "summit": 2, "bilateral": 2, "treaty": 3, "sanctions": 3,
        "ambassador": 2, "embassy": 2, "foreign affairs": 2, "un": 2,
        "united nations": 2, "g20": 3, "g7": 2, "nato": 2, "brics": 2,
        "diplomatic": 2, "negotiation": 2, "peace talks": 3, "accord": 2,
        "alliance": 2, "geopolitical": 2, "normalization": 2,
        "foreign minister": 3, "state visit": 2,
        # Hindi
        "kaatnaiti": 2, "raajnayik": 2, "samjhota": 3, "vaarta": 2,
        "shikhar sammelan": 3, "raajdoot": 2,
    },
    "terrorism": {
        "terrorist": 3, "attack": 2, "isis": 3, "al qaeda": 3,
        "bombing": 2, "hostage": 3, "extremist": 2, "radical": 2,
        "jihad": 3, "insurgent": 2, "militant": 2, "suicide bomber": 3,
        "ied": 3, "counterterrorism": 2, "security forces": 2,
        "terror outfit": 3, "nsa": 2, "intelligence": 1,
        "lashkar": 3, "jaish": 3, "pulwama": 3, "26/11": 3,
        # Hindi
        "aatankvad": 3, "aatanki": 3, "dhamaka": 2, "bandook": 2,
        "barud": 2, "ugravadi": 2,
    },
    "energy": {
        "oil": 2, "crude": 2, "opec": 3, "petroleum": 2, "gas": 1,
        "natural gas": 2, "pipeline": 2, "refinery": 2, "fuel": 2,
        "energy crisis": 3, "power grid": 2, "solar": 2, "renewable": 2,
        "coal": 2, "electricity": 1, "barrel": 2, "brent": 3,
        "oil prices": 3, "strait of hormuz": 3, "lng": 2,
        # Hindi
        "tel": 2, "dharaa": 1, "bijali": 1, "oorja": 2,
        "pertoliyam": 2, "indhan": 2,
    },
    "technology": {
        "ai": 2, "artificial intelligence": 3, "machine learning": 2,
        "startup": 2, "semiconductor": 3, "chip": 2, "5g": 2, "6g": 2,
        "cyber": 2, "hack": 2, "quantum": 2, "upi": 2, "fintech": 2,
        "digital": 1, "blockchain": 2, "crypto": 2, "software": 1,
        "isro": 3, "space": 2, "satellite": 2, "drdo": 3,
        # Hindi
        "takneek": 2, "pradhyogiki": 2, "antriksh": 2,
    },
    "health": {
        "covid": 3, "pandemic": 3, "vaccine": 3, "hospital": 2,
        "disease": 2, "outbreak": 3, "who": 2, "epidemic": 3,
        "doctors": 1, "medical": 1, "health ministry": 2, "icmr": 3,
        "aiims": 3, "surgery": 1, "malaria": 2, "dengue": 2,
        # Hindi
        "swasthy": 2, "aspatal": 2, "bimari": 2, "teeka": 3,
        "mahamari": 3, "ilaj": 1, "chikitsa": 2,
    },
    "environment": {
        "climate": 2, "flood": 2, "earthquake": 3, "cyclone": 3,
        "drought": 2, "pollution": 2, "deforestation": 2, "wildfire": 2,
        "tsunami": 3, "carbon": 2, "emission": 2, "glacier": 2,
        "monsoon": 2, "heatwave": 2, "landslide": 2,
        # Hindi
        "baadh": 2, "bhukamp": 3, "toofan": 3, "sukhaa": 2,
        "pradushan": 2, "jalvayu": 2, "mausam": 1,
    },
}


# Pre-compile all keyword patterns for fast matching
_COMPILED_PATTERNS = {}
for topic, keywords in TOPIC_KEYWORDS.items():
    patterns = []
    for kw, weight in keywords.items():
        # Word boundary match, case insensitive
        patterns.append((re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE), weight))
    _COMPILED_PATTERNS[topic] = patterns


def classify_topic(title: str, content: str, language: str = "en") -> List[Tuple[str, float]]:
    """
    Classify an article into one or more topics based on keyword analysis.

    Returns a list of (topic, confidence) tuples, sorted by confidence descending.
    Only topics with confidence >= 0.15 are returned.
    """
    text = f"{title} {title} {content[:2000]}"  # title weighted 2x

    scores: Counter = Counter()
    max_possible: Counter = Counter()

    for topic, patterns in _COMPILED_PATTERNS.items():
        for pattern, weight in patterns:
            max_possible[topic] += weight
            matches = pattern.findall(text)
            if matches:
                scores[topic] += weight * len(matches)

    # Normalize to 0-1 confidence
    results = []
    for topic in scores:
        if max_possible[topic] > 0:
            # Cap at 1.0, log-scale to avoid single-keyword dominance
            import math
            raw = scores[topic] / max_possible[topic]
            confidence = min(1.0, raw * 2.0)  # boost since most articles won't hit all keywords
            if confidence >= 0.15:
                results.append((topic, round(confidence, 3)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:3]  # Top 3 topics max


def get_primary_topic(title: str, content: str, language: str = "en") -> str:
    """Return the single most likely topic, or 'general' if none matches."""
    topics = classify_topic(title, content, language)
    return topics[0][0] if topics else "general"


def get_topic_tags(title: str, content: str, language: str = "en") -> List[str]:
    """Return a list of topic tag strings for an article."""
    return [t[0] for t in classify_topic(title, content, language)]
