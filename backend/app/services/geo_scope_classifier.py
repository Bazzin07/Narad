"""
Geographic Scope Classifier — determines if an article is India-focused,
global, or mixed.

Uses keyword/entity detection to classify news scope. An article from an
Indian source covering Britney Spears in California → "global".
An article from TOI about Indian budget → "india".

Scope values:
  - "india"  : article is primarily about India or has strong India relevance
  - "global" : article is about international/global events with no India angle
  - "mixed"  : article involves India AND international dimensions (e.g., India-US trade deal)
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── India Signals ─────────────────────────────────────────────────────────────
# High-weight keywords strongly indicate India relevance

INDIA_ENTITIES = {
    # Country
    "india", "bharat", "hindustan", "indian",
    # Government
    "modi", "narendra modi", "pm modi", "rahul gandhi", "amit shah",
    "nirmala sitharaman", "s jaishankar", "jaishankar", "yogi adityanath",
    "mamata banerjee", "arvind kejriwal", "nitish kumar",
    # Institutions
    "lok sabha", "rajya sabha", "supreme court of india", "rbi",
    "reserve bank of india", "sebi", "niti aayog", "isro", "drdo",
    "bcci", "ipl", "ncert", "ugc", "aiims",
    "election commission", "cbi", "nia", "raw", "bse", "nse",
    "sensex", "nifty",
    # Parties
    "bjp", "congress", "aap", "tmc", "shiv sena", "ncp", "jdu", "rjd",
    "dmk", "aiadmk", "bsp", "samajwadi",
    # Major cities
    "mumbai", "delhi", "new delhi", "bangalore", "bengaluru", "hyderabad",
    "chennai", "kolkata", "pune", "ahmedabad", "jaipur", "lucknow",
    "chandigarh", "bhopal", "patna", "thiruvananthapuram", "kochi",
    "guwahati", "srinagar", "jammu", "varanasi", "noida", "gurgaon",
    "gurugram", "indore", "nagpur", "coimbatore", "visakhapatnam",
    # States / UTs
    "maharashtra", "karnataka", "tamil nadu", "telangana", "uttar pradesh",
    "rajasthan", "gujarat", "west bengal", "madhya pradesh", "bihar",
    "kerala", "andhra pradesh", "odisha", "jharkhand", "chhattisgarh",
    "punjab", "haryana", "uttarakhand", "himachal pradesh", "assam",
    "goa", "tripura", "meghalaya", "manipur", "mizoram", "nagaland",
    "arunachal pradesh", "sikkim", "jammu and kashmir", "kashmir",
    "ladakh", "puducherry", "lakshadweep",
    # Indian-specific terms
    "rupee", "inr", "crore", "lakh",
    "aadhaar", "upi", "jan dhan", "swachh bharat", "make in india",
    "atmanirbhar", "digital india", "startup india",
    # Cricket (distinctly Indian interest)
    "ipl", "bcci", "virat kohli", "rohit sharma", "ms dhoni",
    "jasprit bumrah", "abhishek sharma",
    # Defence-specific
    "loc", "line of control", "lac", "line of actual control",
    "indian army", "indian navy", "indian air force",
    "tejas", "arjun tank", "ins vikrant", "agni missile",
    "brahmos", "sukhoi",
    # Cultural / Festivals / Lifestyle (Indian-specific)
    "holi", "diwali", "durga puja", "navratri", "ganesh chaturthi",
    "makar sankranti", "pongal", "onam", "lohri", "baisakhi",
    "chhath", "eid", "raksha bandhan", "janmashtami", "ram navami",
    "rashifal", "rashi", "kundli", "panchang",
    # Bollywood / Indian entertainment
    "bollywood", "priyanka chopra", "shah rukh khan", "salman khan",
    "aamir khan", "amitabh bachchan", "deepika padukone", "alia bhatt",
    "ranveer singh", "katrina kaif", "akshay kumar",
    # Indian rivers / geography
    "ganga", "yamuna", "godavari", "brahmaputra", "narmada",
    # Hindi keywords
    "bharat", "sarkaar", "pradhan mantri", "mukhya mantri",
    "chunav", "vikas", "garib", "kisan", "arthvyavastha",
    "mehngai", "desh", "hindustan",
}

# Compile patterns for whole-word matching
_INDIA_PATTERNS = [
    (re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE), len(kw.split()))
    for kw in sorted(INDIA_ENTITIES, key=len, reverse=True)  # longest first
]


def classify_geo_scope(
    title: str,
    content: str,
    source_region: Optional[str] = None,
    language: Optional[str] = None,
) -> str:
    """
    Classify whether an article is India-focused, global, or mixed.

    Returns: "india", "global", or "mixed"
    """
    text = f"{title} {title} {content[:2000]}"  # title weighted 2x

    # Count India signals
    india_hits = 0
    india_unique = set()

    for pattern, word_count in _INDIA_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            india_hits += len(matches) * word_count
            india_unique.add(pattern.pattern.lower())

    # Indian language articles with any India signal → india scope
    india_languages = {"hi", "ta", "bn", "te", "mr", "gu", "kn", "ml", "pa", "ur", "or"}
    is_indian_language = language in india_languages

    # Strong India relevance: 3+ unique India entities or 6+ total hits
    strong_india = len(india_unique) >= 3 or india_hits >= 6

    # Moderate India relevance: at least 1 unique entity
    moderate_india = len(india_unique) >= 1

    # Source region hint
    is_india_source = source_region == "india"

    # Classification logic:
    if strong_india:
        return "india"
    elif is_indian_language:
        # Indian language articles with even weak India signals → india
        return "india" if moderate_india else "mixed"
    elif moderate_india and is_india_source:
        # Indian source + some India signal → mixed or india
        return "mixed" if india_hits < 4 else "india"
    elif moderate_india:
        # Global source mentions India → mixed
        return "mixed"
    else:
        return "global"


def classify_geo_scope_batch(articles: list) -> list:
    """Classify geographic scope for a batch of article dicts."""
    return [
        classify_geo_scope(
            title=a.get("title", ""),
            content=a.get("content", ""),
            source_region=a.get("source_region"),
            language=a.get("language"),
        )
        for a in articles
    ]


# ── State Extraction ─────────────────────────────────────────────────────────
# Maps city/region keywords to canonical Indian state names

INDIAN_STATES = {
    # Delhi NCR
    "delhi": "delhi", "new delhi": "delhi",
    # Maharashtra
    "mumbai": "maharashtra", "maharashtra": "maharashtra", "pune": "maharashtra",
    "nagpur": "maharashtra", "thane": "maharashtra", "nashik": "maharashtra",
    # Karnataka
    "bangalore": "karnataka", "bengaluru": "karnataka", "karnataka": "karnataka",
    "mysore": "karnataka", "mysuru": "karnataka", "mangalore": "karnataka",
    # Tamil Nadu
    "chennai": "tamil_nadu", "tamil nadu": "tamil_nadu", "coimbatore": "tamil_nadu",
    "madurai": "tamil_nadu", "salem": "tamil_nadu", "trichy": "tamil_nadu",
    # Telangana
    "hyderabad": "telangana", "telangana": "telangana", "secunderabad": "telangana",
    "warangal": "telangana",
    # West Bengal
    "kolkata": "west_bengal", "west bengal": "west_bengal", "howrah": "west_bengal",
    "siliguri": "west_bengal", "durgapur": "west_bengal",
    # Uttar Pradesh
    "lucknow": "uttar_pradesh", "uttar pradesh": "uttar_pradesh",
    "noida": "uttar_pradesh", "varanasi": "uttar_pradesh", "agra": "uttar_pradesh",
    "kanpur": "uttar_pradesh", "prayagraj": "uttar_pradesh", "allahabad": "uttar_pradesh",
    "meerut": "uttar_pradesh", "ghaziabad": "uttar_pradesh", "mathura": "uttar_pradesh",
    "ayodhya": "uttar_pradesh",
    # Bihar
    "patna": "bihar", "bihar": "bihar", "gaya": "bihar", "muzaffarpur": "bihar",
    # Rajasthan
    "jaipur": "rajasthan", "rajasthan": "rajasthan", "jodhpur": "rajasthan",
    "udaipur": "rajasthan", "kota": "rajasthan", "ajmer": "rajasthan",
    # Gujarat
    "ahmedabad": "gujarat", "gujarat": "gujarat", "surat": "gujarat",
    "vadodara": "gujarat", "rajkot": "gujarat", "gandhinagar": "gujarat",
    # Madhya Pradesh
    "bhopal": "madhya_pradesh", "madhya pradesh": "madhya_pradesh",
    "indore": "madhya_pradesh", "jabalpur": "madhya_pradesh", "gwalior": "madhya_pradesh",
    # Kerala
    "thiruvananthapuram": "kerala", "kochi": "kerala", "kerala": "kerala",
    "kozhikode": "kerala", "calicut": "kerala", "thrissur": "kerala",
    # Assam
    "guwahati": "assam", "assam": "assam", "dibrugarh": "assam",
    # J&K
    "srinagar": "jammu_and_kashmir", "jammu": "jammu_and_kashmir",
    "kashmir": "jammu_and_kashmir", "jammu and kashmir": "jammu_and_kashmir",
    # Punjab
    "chandigarh": "punjab", "punjab": "punjab", "amritsar": "punjab",
    "ludhiana": "punjab", "jalandhar": "punjab",
    # Haryana
    "gurgaon": "haryana", "gurugram": "haryana", "haryana": "haryana",
    "faridabad": "haryana", "karnal": "haryana", "panipat": "haryana",
    # Goa
    "goa": "goa", "panaji": "goa",
    # Uttarakhand
    "uttarakhand": "uttarakhand", "dehradun": "uttarakhand",
    "haridwar": "uttarakhand", "rishikesh": "uttarakhand",
    # Himachal Pradesh
    "shimla": "himachal_pradesh", "himachal pradesh": "himachal_pradesh",
    "dharamshala": "himachal_pradesh", "manali": "himachal_pradesh",
    # Andhra Pradesh
    "andhra pradesh": "andhra_pradesh", "visakhapatnam": "andhra_pradesh",
    "vijayawada": "andhra_pradesh", "amaravati": "andhra_pradesh",
    "tirupati": "andhra_pradesh",
    # Odisha
    "odisha": "odisha", "bhubaneswar": "odisha", "cuttack": "odisha", "puri": "odisha",
    # Jharkhand
    "jharkhand": "jharkhand", "ranchi": "jharkhand", "jamshedpur": "jharkhand",
    # Chhattisgarh
    "chhattisgarh": "chhattisgarh", "raipur": "chhattisgarh",
    # Ladakh
    "ladakh": "ladakh", "leh": "ladakh",
    # Tripura
    "tripura": "tripura", "agartala": "tripura",
    # Meghalaya
    "meghalaya": "meghalaya", "shillong": "meghalaya",
    # Manipur
    "manipur": "manipur", "imphal": "manipur",
    # Mizoram
    "mizoram": "mizoram", "aizawl": "mizoram",
    # Nagaland
    "nagaland": "nagaland", "kohima": "nagaland",
    # Arunachal Pradesh
    "arunachal pradesh": "arunachal_pradesh", "itanagar": "arunachal_pradesh",
    # Sikkim
    "sikkim": "sikkim", "gangtok": "sikkim",
    # Puducherry
    "puducherry": "puducherry", "pondicherry": "puducherry",
}

# Pre-compile patterns for state extraction (longest first for accuracy)
_STATE_PATTERNS = [
    (re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE), state)
    for kw, state in sorted(INDIAN_STATES.items(), key=lambda x: len(x[0]), reverse=True)
]


def extract_state(title: str, content: str) -> str | None:
    """
    Extract primary Indian state from article text.
    Returns canonical state name or None if no state detected.
    """
    text = f"{title} {title} {content[:1000]}"  # title weighted 2x

    state_hits: dict[str, int] = {}
    for pattern, state in _STATE_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            state_hits[state] = state_hits.get(state, 0) + len(matches)

    if not state_hits:
        return None

    # Return the most-mentioned state
    return max(state_hits, key=state_hits.get)
