"""
Entity Extraction Service — language-aware NLP with cross-lingual entity matching.

English: uses en_core_web_sm (best quality for English)
Other languages: uses xx_ent_wiki_sm (multilingual, 100+ languages)

Cross-lingual entity matching:
  - Transliterates all entities to Latin script using `unidecode`
  - Uses fuzzy matching to find shared entities across languages
  - "जापान" (Hindi) ↔ "Japan" (English) now resolves correctly

No LLM calls. Deterministic extraction.
"""
import logging
import re
from typing import List, Tuple, Set
from difflib import SequenceMatcher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, Entity, ArticleEntity

logger = logging.getLogger(__name__)

# ── Amazon Comprehend (AWS-native NER for EN/HI/UR) ───────────────────────────
_comprehend_client = None

# Languages supported by Amazon Comprehend (subset of Narad's 12)
COMPREHEND_SUPPORTED = {"en", "hi", "ar", "ur"}  # ur maps to ar in Comprehend

# Entity type mapping from Comprehend to spaCy-compatible types
COMPREHEND_TYPE_MAP = {
    "PERSON": "PERSON",
    "ORGANIZATION": "ORG",
    "LOCATION": "GPE",
    "COMMERCIAL_ITEM": "ORG",
    "EVENT": "EVENT",
    "OTHER": "MISC",
    "QUANTITY": None,
    "DATE": None,
    "TITLE": None,
}


def _get_comprehend():
    """Lazy-load Amazon Comprehend client."""
    global _comprehend_client
    if _comprehend_client is None:
        try:
            import boto3
            from app.config import settings
            _comprehend_client = boto3.client("comprehend", region_name=settings.aws_region)
            logger.info("Amazon Comprehend client initialized")
        except Exception as e:
            logger.warning(f"Comprehend not available: {e}")
            _comprehend_client = False  # Sentinel to avoid repeated attempts
    return _comprehend_client if _comprehend_client else None


def extract_entities_comprehend(text: str, language: str = "en") -> List[Tuple[str, str, str]]:
    """
    Extract named entities using Amazon Comprehend (AWS-native AI).
    Returns [] if language unsupported, Comprehend unavailable, or an error occurs.
    """
    comprehend = _get_comprehend()
    if not comprehend:
        return []
    lang_code = "ar" if language == "ur" else language
    if lang_code not in {"en", "hi", "ar"}:
        return []
    try:
        text_trimmed = text[:4800] if len(text.encode("utf-8")) > 4800 else text
        response = comprehend.detect_entities(Text=text_trimmed, LanguageCode=lang_code)
        entities = []
        seen: Set[tuple] = set()
        for ent in response.get("Entities", []):
            mapped_type = COMPREHEND_TYPE_MAP.get(ent["Type"])
            if not mapped_type or ent["Score"] < 0.70:
                continue
            text_val = ent["Text"].strip()
            normalized = normalize_entity_text(text_val)
            key = (normalized, mapped_type)
            if key not in seen and len(text_val) >= 2:
                entities.append((text_val, mapped_type, normalized))
                seen.add(key)
        logger.debug(f"Comprehend found {len(entities)} entities [{language}]")
        return entities
    except Exception as e:
        logger.warning(f"Comprehend entity extraction failed: {e}")
        return []


def get_sentiment_comprehend(text: str, language: str = "en"):
    """
    Get sentiment score from Amazon Comprehend.
    Returns float in -1.0..1.0 range, or None if unavailable / language unsupported.
    """
    comprehend = _get_comprehend()
    if not comprehend:
        return None
    lang_code = "ar" if language == "ur" else language
    if lang_code not in {"en", "hi", "ar"}:
        return None
    try:
        text_trimmed = text[:4800] if len(text.encode("utf-8")) > 4800 else text
        response = comprehend.detect_sentiment(Text=text_trimmed, LanguageCode=lang_code)
        sentiment = response["Sentiment"]
        scores = response["SentimentScore"]
        if sentiment == "POSITIVE":
            return scores["Positive"]
        elif sentiment == "NEGATIVE":
            return -scores["Negative"]
        elif sentiment == "MIXED":
            return scores["Positive"] - scores["Negative"]
        else:
            return 0.0
    except Exception as e:
        logger.warning(f"Comprehend sentiment failed: {e}")
        return None


# ── Lazy-load spaCy models ────────────────────────────────────────────────────
_nlp_en = None
_nlp_xx = None
_unidecode_fn = None



def _get_unidecode():
    """Lazy-load unidecode for transliteration."""
    global _unidecode_fn
    if _unidecode_fn is None:
        try:
            from unidecode import unidecode
            _unidecode_fn = unidecode
        except ImportError:
            logger.warning("unidecode not installed — entity normalization disabled")
            _unidecode_fn = lambda x: x
    return _unidecode_fn


def normalize_entity_text(text: str) -> str:
    """
    Normalize entity text for cross-lingual matching.
    1. Transliterate to Latin script (जापान → jaapaan)
    2. Remove apostrophes (unidecode artifacts)
    3. Lowercase
    4. Strip extra whitespace and punctuation
    """
    unidecode = _get_unidecode()
    normalized = unidecode(text)
    normalized = normalized.lower().strip()
    normalized = re.sub(r"['\"\-]", "", normalized)     # remove quotes & hyphens
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def fuzzy_match(text1: str, text2: str, threshold: float = 0.60) -> bool:
    """
    Check if two normalized entity texts are a fuzzy match.
    Uses SequenceMatcher for efficiency.
    threshold=0.60 catches: iiraan↔iran, kh'aameneii↔khamenei, etc.
    """
    if text1 == text2:
        return True
    ratio = SequenceMatcher(None, text1, text2).ratio()
    return ratio >= threshold


def _get_nlp_en():
    """Load English spaCy model."""
    global _nlp_en
    if _nlp_en is None:
        import spacy
        try:
            _nlp_en = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy model: en_core_web_sm")
        except OSError:
            logger.error("spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm")
            raise
    return _nlp_en


def _get_nlp_xx():
    """Load multilingual spaCy model for non-English."""
    global _nlp_xx
    if _nlp_xx is None:
        import spacy
        try:
            _nlp_xx = spacy.load("xx_ent_wiki_sm")
            logger.info("Loaded spaCy model: xx_ent_wiki_sm")
        except OSError:
            logger.warning(
                "xx_ent_wiki_sm not found — falling back to en_core_web_sm for all languages. "
                "Install with: python -m spacy download xx_ent_wiki_sm"
            )
            _nlp_xx = _get_nlp_en()
    return _nlp_xx


# Entity types we care about
ENTITY_TYPES = {"PERSON", "ORG", "GPE", "NORP", "EVENT", "LOC", "PER", "MISC"}


class EntityService:
    """Extracts and stores named entities using language-aware spaCy NER with cross-lingual matching."""

    def _get_nlp_for_language(self, language: str = "en"):
        """Route to the right spaCy model based on article language."""
        if language == "en":
            return _get_nlp_en()
        return _get_nlp_xx()

    def extract_entities(self, text: str, language: str = "en") -> List[Tuple[str, str, str]]:
        """
        Extract entities from text using language-appropriate model.

        Strategy:
          - EN / HI / UR: Amazon Comprehend (AWS-native AI) + spaCy merge
          - All other Indian languages: spaCy dual-pass NER only

        Returns list of (entity_text, entity_type, normalized_text) tuples.
        """
        if len(text) > 100_000:
            text = text[:100_000]

        entities: Set[Tuple[str, str, str]] = set()

        # ── AWS Comprehend layer (EN / HI / UR) ──────────────────────────────
        if language in COMPREHEND_SUPPORTED:
            comprehend_entities = extract_entities_comprehend(text, language)
            for item in comprehend_entities:
                entities.add(item)

        # ── spaCy layer ───────────────────────────────────────────────────────
        if language == "en":
            # English: single pass with en model (Comprehend already ran, this fills gaps)
            nlp = _get_nlp_en()
            doc = nlp(text[:100_000])
            for ent in doc.ents:
                if ent.label_ in ENTITY_TYPES:
                    clean = ent.text.strip()
                    if self._is_valid_entity(clean):
                        entities.add((clean, ent.label_, normalize_entity_text(clean)))
        else:
            # Non-English: dual-pass

            # Pass 1: xx model on original script
            try:
                nlp_xx = _get_nlp_xx()
                doc = nlp_xx(text)
                for ent in doc.ents:
                    if ent.label_ in ENTITY_TYPES:
                        clean = ent.text.strip()
                        if self._is_valid_entity(clean, is_foreign=True):
                            entities.add((clean, ent.label_, normalize_entity_text(clean)))
            except Exception as e:
                logger.warning(f"xx NER pass failed: {e}")

            # Pass 2: en model on transliterated text (catches names like Iran, Trump, etc.)
            try:
                unidecode = _get_unidecode()
                transliterated = unidecode(text)
                nlp_en = _get_nlp_en()
                doc = nlp_en(transliterated)
                for ent in doc.ents:
                    if ent.label_ in ENTITY_TYPES:
                        clean = ent.text.strip()
                        if self._is_valid_entity(clean, is_foreign=True):
                            # Store with transliterated form as text, normalized with full cleanup
                            normalized = normalize_entity_text(clean)
                            entities.add((clean, ent.label_, normalized))
            except Exception as e:
                logger.warning(f"en NER transliteration pass failed: {e}")

        return list(entities)

    def _is_valid_entity(self, text: str, is_foreign: bool = False) -> bool:
        """Filter out noise entities."""
        if len(text) < 2 or len(text) > 200:
            return False

        # For foreign scripts, reject very short transliterated forms (noise)
        if is_foreign:
            normalized = normalize_entity_text(text)
            # Reject if normalized form is less than 3 chars (likely noise like "hai", "ki")
            if len(normalized) < 3:
                return False
            # Reject common Hindi stop words that get tagged as entities
            noise_words = {
                "hai", "hain", "ke", "ki", "ka", "ko", "me", "men",
                "se", "par", "kaa", "kii", "ek", "yah", "ye", "vo",
                "or", "aur", "bhii", "jo", "jis", "un", "in",
            }
            if normalized in noise_words:
                return False

        return True

    async def process_article(self, article: Article, db: AsyncSession) -> List[Tuple[str, str, str]]:
        """Extract entities from an article and store them."""
        try:
            full_text = f"{article.title}. {article.content}"
            lang = getattr(article, 'language', 'en') or 'en'
            raw_entities = self.extract_entities(full_text, language=lang)

            if not raw_entities:
                logger.info(f"No entities found for article {article.id} [{lang}]")
                article.processed = max(article.processed, 1)
                await db.flush()
                return []

            await self._store_entities(article.id, raw_entities, db)

            article.processed = max(article.processed, 1)
            await db.flush()

            logger.info(f"Extracted {len(raw_entities)} entities from article {article.id} [{lang}]")
            return raw_entities

        except Exception as e:
            logger.error(f"Entity extraction failed for article {article.id}: {e}")
            return []

    async def _store_entities(
        self, article_id: str, entities: List[Tuple[str, str, str]], db: AsyncSession
    ) -> None:
        """Upsert entities and create article-entity associations."""
        for entity_text, entity_type, normalized in entities:
            result = await db.execute(
                select(Entity).where(Entity.text == entity_text, Entity.type == entity_type)
            )
            entity = result.scalar_one_or_none()

            if entity is None:
                entity = Entity(text=entity_text, type=entity_type, normalized_text=normalized)
                db.add(entity)
                await db.flush()
            elif entity.normalized_text is None:
                # backfill normalized_text for existing entities
                entity.normalized_text = normalized

            result = await db.execute(
                select(ArticleEntity).where(
                    ArticleEntity.article_id == article_id,
                    ArticleEntity.entity_id == entity.id,
                )
            )
            if result.scalar_one_or_none() is None:
                assoc = ArticleEntity(article_id=article_id, entity_id=entity.id)
                db.add(assoc)

    async def get_article_entities(self, article_id: str, db: AsyncSession) -> List[dict]:
        """Get all entities for an article."""
        result = await db.execute(
            select(Entity)
            .join(ArticleEntity, ArticleEntity.entity_id == Entity.id)
            .where(ArticleEntity.article_id == article_id)
        )
        entities = result.scalars().all()
        return [
            {"text": e.text, "type": e.type, "id": e.id,
             "normalized": e.normalized_text or normalize_entity_text(e.text)}
            for e in entities
        ]

    async def get_shared_entities(
        self, article1_id: str, article2_id: str, db: AsyncSession
    ) -> List[dict]:
        """
        Get entities shared between two articles using cross-lingual fuzzy matching.
        Type-agnostic: 'Iran' (GPE) still matches 'ईरान' (ORG) because NER models
        tag the same entity differently across languages.
        """
        entities1 = await self.get_article_entities(article1_id, db)
        entities2 = await self.get_article_entities(article2_id, db)

        shared = []
        matched_ids_2 = set()

        for e1 in entities1:
            norm1 = e1["normalized"]
            if len(norm1) < 3:
                continue
            for e2 in entities2:
                if e2["id"] in matched_ids_2:
                    continue
                norm2 = e2["normalized"]
                if len(norm2) < 3:
                    continue

                # Fuzzy match on normalized text — type-agnostic for cross-lingual
                if fuzzy_match(norm1, norm2):
                    # Use the English version if available
                    display_text = e1["text"] if e1["text"].isascii() else e2["text"]
                    if not e2["text"].isascii() and not e1["text"].isascii():
                        display_text = e1["text"]
                    shared.append({
                        "text": display_text,
                        "type": e1["type"],
                        "variants": [e1["text"], e2["text"]],
                    })
                    matched_ids_2.add(e2["id"])
                    break

        return shared

    async def get_shared_entity_count(
        self, article1_id: str, article2_id: str, db: AsyncSession
    ) -> float:
        """
        Calculate entity overlap score (Jaccard-like) with fuzzy cross-lingual matching.
        Type-agnostic matching for cross-lingual robustness.
        """
        entities1 = await self.get_article_entities(article1_id, db)
        entities2 = await self.get_article_entities(article2_id, db)

        if not entities1 or not entities2:
            return 0.0

        # Filter out very short normalized forms
        ents1 = [e for e in entities1 if len(e["normalized"]) >= 3]
        ents2 = [e for e in entities2 if len(e["normalized"]) >= 3]

        if not ents1 or not ents2:
            return 0.0

        # Count fuzzy matches (type-agnostic)
        match_count = 0
        used = set()
        for e1 in ents1:
            for j, e2 in enumerate(ents2):
                if j in used:
                    continue
                if fuzzy_match(e1["normalized"], e2["normalized"]):
                    match_count += 1
                    used.add(j)
                    break

        union_size = len(ents1) + len(ents2) - match_count
        if union_size == 0:
            return 0.0

        return match_count / union_size

    async def process_unprocessed(self, db: AsyncSession, limit: int = 50) -> int:
        """Process articles that haven't had entity extraction yet."""
        result = await db.execute(
            select(Article).where(Article.processed < 1).limit(limit)
        )
        articles = result.scalars().all()

        count = 0
        for article in articles:
            entities = await self.process_article(article, db)
            if entities:
                count += 1

        await db.commit()
        logger.info(f"Entity extraction: processed {count}/{len(articles)} articles")
        return count
