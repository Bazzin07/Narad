"""
Page-Index RAG Service — chunk articles into pages, build a mini FAISS index,
retrieve the most relevant chunks for a query, then answer with Nova Pro.

Architecture:
  1. Chunking  — each article split into ~300-token "pages"
  2. In-memory FAISS index per session (not persisted — ephemeral)
  3. Query embedding matches top-k pages (cross-article)
  4. Pages assembled into a RAG context window
  5. Nova Pro generates a grounded, cited answer

Cost controls:
  - Total tokens per call capped at 1,800 (question + pages)
  - Haiku used first; Nova Pro used when Haiku is tripped/unavailable
  - All answers cached by SHA-256(question) for 20 min
"""
import logging
import hashlib
import textwrap
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
PAGE_SIZE = 300         # chars per chunk (≈ 75 tokens)
OVERLAP = 50            # chars of overlap between consecutive pages
MAX_PAGES_RETRIEVED = 5 # top-k pages to push into context
MAX_CONTEXT_CHARS = 4_000  # hard cap for the assembled RAG context


# ── Page Indexer ─────────────────────────────────────────────────────────────

class PageIndex:
    """
    In-memory per-request page index.

    Build once per ask-narad call; queryable for top-k relevant chunks.
    """

    def __init__(self, embedding_service):
        self.embedding_service = embedding_service
        self.pages: List[dict] = []          # {text, article_id, title, source, page_no}
        self._embeddings: Optional[np.ndarray] = None

    def build(self, articles: List[dict]) -> int:
        """
        Chunk all articles into pages and embed them.
        Returns number of pages indexed.
        """
        all_texts: List[str] = []

        for art in articles:
            content = (art.get("content") or "")[:8_000]
            title   = art.get("title", "")
            source  = art.get("source", "")
            art_id  = art.get("id", "")

            # Window-based chunking with overlap
            pages = _chunk(content, PAGE_SIZE, OVERLAP)
            for i, page_text in enumerate(pages):
                # Prepend article title as context anchor
                full_text = f"[{source}] {title}\n{page_text}"
                self.pages.append({
                    "text": full_text,
                    "article_id": art_id,
                    "title": title,
                    "source": source,
                    "url": art.get("url", ""),
                    "published_at": art.get("published_at", ""),
                    "page_no": i,
                })
                all_texts.append(full_text)

        if not all_texts:
            return 0

        # Batch embed all pages (local model — $0 cost)
        try:
            from app.services.embedding_service import _get_model
            model = _get_model()
            embeddings = model.encode(all_texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
            self._embeddings = embeddings.astype(np.float32)
            logger.info(f"PageIndex: indexed {len(self.pages)} pages from {len(articles)} articles")
        except Exception as e:
            logger.error(f"PageIndex embed failed: {e}")
            self._embeddings = None

        return len(self.pages)

    def query(self, question: str, top_k: int = MAX_PAGES_RETRIEVED) -> List[dict]:
        """
        Retrieve top-k pages most relevant to the question.
        Returns list of page dicts sorted by relevance.
        """
        if self._embeddings is None or len(self.pages) == 0:
            return []

        try:
            from app.services.embedding_service import _get_model
            model = _get_model()
            q_emb = model.encode([question], normalize_embeddings=True)[0].astype(np.float32)

            # Cosine similarity (dot product on normalized vecs)
            scores = self._embeddings @ q_emb
            top_k = min(top_k, len(self.pages))
            top_indices = np.argsort(scores)[::-1][:top_k]

            results = []
            seen_articles = set()
            for idx in top_indices:
                page = self.pages[idx]
                score = float(scores[idx])
                if score < 0.2:          # relevance threshold
                    continue
                page_copy = dict(page)
                page_copy["relevance_score"] = round(score, 3)
                # De-duplicate by article — max 2 pages per article
                art_count = sum(1 for r in results if r["article_id"] == page["article_id"])
                if art_count < 2:
                    results.append(page_copy)
            return results
        except Exception as e:
            logger.error(f"PageIndex query failed: {e}")
            return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _chunk(text: str, size: int, overlap: int) -> List[str]:
    """Split text into overlapping windows."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks


def build_rag_context(pages: List[dict]) -> str:
    """Assemble page chunks into a context string for the LLM prompt."""
    parts = []
    total_chars = 0
    for page in pages:
        block = (
            f"--- Source: {page['source']} | {page['title'][:80]} "
            f"(page {page['page_no']+1}) ---\n"
            f"{page['text'][:PAGE_SIZE + OVERLAP]}"
        )
        if total_chars + len(block) > MAX_CONTEXT_CHARS:
            break
        parts.append(block)
        total_chars += len(block)
    return "\n\n".join(parts)


def question_cache_key(question: str) -> str:
    """Deterministic cache key for a user question."""
    return hashlib.sha256(question.strip().lower().encode()).hexdigest()[:16]
