"""
LLM Service — user-friendly explanations for news analysis.

Covers ALL news domains: politics, military, economy, sports, technology,
health, entertainment, environment, crime, science, culture, and more.

Two features:
  1. Deep Analysis — explain a single news event with context and implications
  2. Impact Analysis — explain how two events from different domains affect each other

Supports two backends:
  - "bedrock": Real Amazon Bedrock (Claude 3 Sonnet)
  - "mock": Local mock for development/testing
"""
import json
import logging
from typing import List, Optional

from app.config import settings
from app.services.scoring_service import RelationScore
from app.services.llm_cache import llm_cache
from app.services.llm_rate_limiter import llm_rate_limiter

logger = logging.getLogger(__name__)


# ── Prompt: Deep Analysis of a Single Article ──────────────────────────────────

DEEP_ANALYSIS_PROMPT = """You are a world-class news analyst writing for a general audience.

Analyze this news event and provide a clear, insightful breakdown that helps a regular person understand what's happening and why it matters.

== NEWS EVENT ==
Title: {title}
Source: {source}
Published: {published}
Content: {content}

== DETECTED CONTEXT ==
Key People/Organizations/Places: {entities}
Related Event Cluster: {cluster_info}

== YOUR ANALYSIS (write in plain language, no jargon) ==

Provide:
1. **What Happened** — A clear 5-6 sentence summary anyone can understand
2. **Why It Matters** — The real-world significance and who is affected
3. **Background Context** — Brief historical/political context that helps make sense of this
4. **What Could Happen Next** — Potential implications and ripple effects
5. **Key Players** — Who are the important people/organizations involved and their roles

Keep it conversational and clear. Imagine you're explaining this to a smart friend over coffee.

IMPORTANT: Write your entire response in {output_language}."""


# ── Prompt: Impact Analysis Between Two Articles ──────────────────────────────

IMPACT_ANALYSIS_PROMPT = """You are a senior geopolitical and intelligence analyst providing a detailed, professional briefing.

Your task is to analyze two news events and explain their underlying connection, cause-and-effect relationship, and real-world implications. Your analysis must be highly detailed, well-structured, and easy to scan.

== EVENT 1 ==
Title: {title1}
Source: {source1}
Published: {published1}
Content: {content1}

== EVENT 2 ==
Title: {title2}
Source: {source2}
Published: {published2}
Content: {content2}

== DETECTED CONNECTION SIGNALS ==
Shared themes/entities: {shared_entities_text}
Connection strength: {confidence} ({total_score_pct}% match)
Time context: {time_context}

== YOUR ANALYSIS ==

Please structure your briefing using the following strict format. Use Markdown, clear headings, and bullet points. Do not use filler introductions or conclusions.

### 🔗 The Core Connection
Provide a precise, detailed explanation of how these two events are structurally or causally linked. Explain the mechanism connecting them (e.g., economic pressure, diplomatic retaliation, parallel technological trends).

### 💥 Direct Impact
- Detail exactly who or what is affected by this connection.
- Outline the immediate consequences observed in the reports.

### 🌍 The Bigger Picture
- Zoom out and explain the broader trend, strategy, or historical context.
- Why does this interconnected development matter on a larger scale?

### 🔮 What to Watch Next
- Provide 2-3 specific, actionable indicators or future events that readers should monitor closely to see how this situation evolves.

Write with the authoritative, clear tone of a premium intelligence newsletter (e.g., Stratfor, Economist).
IMPORTANT: Write your entire response in {output_language}."""


# ── Prompt: Overall Probe Summary ───────────────────────────────────────────

PROBE_SUMMARY_PROMPT = """You are a senior geopolitical and intelligence analyst providing a detailed, professional briefing.

A user has submitted a piece of news or text, and we have searched our intelligence corpus for related events. Your task is to provide an executive summary of how the user's text fits into the broader picture formed by these related events.

== THE PROBE TEXT ==
Source: {query_source}
Text: {query_text}

== CORPUS MATCHES ==
{matches_text}

== YOUR BRIEFING ==

Please summarize the narrative landscape based on these matches. Use Markdown, clear headings, and bullet points. Do not use filler introductions.

### 📰 The Narrative Landscape
Provide a holistic overview of what the corpus reveals about the submitted text. Is this part of a larger ongoing story? Are there multiple angles being reported? 

### 🎯 Key Intersections
- Highlight the strongest thematic or entity connections between the probe text and the corpus.
- What specific issues, people, or regions tie these stories together?

### 📉 Intelligence Gaps & Weak Signals
- If the matches are weak, explain what context is missing from the corpus.
- If the matches are strong, point out any conflicting information or divergent reporting among the sources.

Write with an authoritative, clear tone (e.g., Stratfor, Economist). Focus only on facts presented in the text and the matches.
IMPORTANT: Write your entire response in {output_language}."""


class LLMService:
    """Base service with prompt formatting and fallback logic."""

    def format_deep_analysis(
        self, article: dict, entities: list, cluster_info: str,
        preferred_language: str = "English",
    ) -> str:
        """Format prompt for single article deep analysis."""
        entity_names = [e.get("text", str(e)) for e in entities] if entities else ["None detected"]

        return DEEP_ANALYSIS_PROMPT.format(
            title=article.get("title", "Unknown"),
            source=article.get("source", "Unknown"),
            published=str(article.get("published_at", "")),
            content=article.get("content", "")[:1500],
            entities=", ".join(entity_names),
            cluster_info=cluster_info or "No related cluster detected",
            output_language=preferred_language,
        )

    def format_impact_analysis(
        self,
        article1: dict,
        article2: dict,
        score: RelationScore,
        shared_entities: List[dict],
        preferred_language: str = "English",
    ) -> str:
        """Format prompt for cross-domain impact analysis."""
        # Build readable time context
        try:
            from datetime import datetime
            t1 = article1.get("published_at", "")
            t2 = article2.get("published_at", "")
            if isinstance(t1, str) and t1:
                t1 = datetime.fromisoformat(t1)
            if isinstance(t2, str) and t2:
                t2 = datetime.fromisoformat(t2)
            if isinstance(t1, datetime) and isinstance(t2, datetime):
                diff = abs((t1 - t2).total_seconds()) / 3600
                if diff < 1:
                    time_context = "within the same hour"
                elif diff < 24:
                    time_context = f"within {int(diff)} hours of each other"
                else:
                    time_context = f"about {int(diff / 24)} days apart"
            else:
                time_context = "around the same time period"
        except Exception:
            time_context = "around the same time period"

        entity_names = [e.get("text", str(e)) for e in shared_entities] if shared_entities else []
        if entity_names:
            shared_text = f"common references to {', '.join(entity_names)}"
        else:
            shared_text = "thematic connections (no direct shared names/places)"

        return IMPACT_ANALYSIS_PROMPT.format(
            title1=article1.get("title", "Unknown"),
            source1=article1.get("source", "Unknown"),
            published1=str(article1.get("published_at", "")),
            content1=article1.get("content", "")[:1000],
            title2=article2.get("title", "Unknown"),
            source2=article2.get("source", "Unknown"),
            published2=str(article2.get("published_at", "")),
            content2=article2.get("content", "")[:1000],
            shared_entities_text=shared_text,
            confidence=score.confidence,
            total_score_pct=f"{score.total_score * 100:.0f}",
            time_context=time_context,
            output_language=preferred_language,
        )

    def fallback_deep_analysis(self, article: dict, entities: list, cluster_info: str) -> str:
        """Generate a rich news analysis without LLM — reads like real journalism."""
        title = article.get("title", "Unknown Event")
        content = article.get("content", "")
        source = article.get("source", "Unknown")
        entity_names = [e.get("text", str(e)) for e in entities] if entities else []

        # Extract meaningful content
        sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 20]

        parts = []

        # What Happened
        summary_text = '. '.join(sentences[:4]) + '.' if sentences else content[:400]
        parts.append(f"**What Happened**\n\n{summary_text}")

        # Why It Matters
        if entity_names:
            key_players = ', '.join(entity_names[:5])
            parts.append(
                f"**Why It Matters**\n\n"
                f"This development involves {key_players} and could have significant "
                f"implications beyond the immediate story. "
                f"The involvement of these key players suggests this is not an isolated "
                f"incident but part of larger ongoing dynamics."
            )
        else:
            parts.append(
                f"**Why It Matters**\n\n"
                f"This event could have far-reaching consequences beyond its immediate impact. "
                f"It signals shifting dynamics that people should monitor closely."
            )

        # Background Context
        if len(sentences) > 4:
            context_text = '. '.join(sentences[4:7]) + '.'
            parts.append(f"**Background Context**\n\n{context_text}")
        else:
            parts.append(
                f"**Background Context**\n\n"
                f"This event comes at a time of rapid developments, where news "
                f"in one area can quickly cascade into effects across related domains and regions."
            )

        # Related Coverage
        if cluster_info and cluster_info != "No related cluster detected":
            parts.append(
                f"**Related Coverage**\n\n"
                f"This story is part of a broader cluster of developments — {cluster_info}. "
                f"Multiple sources are tracking this evolving situation."
            )

        # What to Watch
        parts.append(
            f"**What to Watch**\n\n"
            f"Keep an eye on official statements and policy responses in the coming days. "
            f"The way key stakeholders respond will determine whether this escalates "
            f"or leads to a resolution."
        )

        parts.append(f"*Source: {source}*")

        return "\n\n".join(parts)

    def fallback_impact_analysis(self, score: RelationScore, shared_entities: List[dict],
                                  article1: dict, article2: dict) -> str:
        """Generate a rich cross-event impact analysis without LLM."""
        title1 = article1.get("title", "Event 1")
        title2 = article2.get("title", "Event 2")
        content1 = article1.get("content", "")[:500]
        content2 = article2.get("content", "")[:500]
        source1 = article1.get("source", "Unknown")
        source2 = article2.get("source", "Unknown")
        entity_names = [e.get("text", str(e)) for e in shared_entities] if shared_entities else []

        parts = []

        # Connection Analysis
        if score.confidence == "Strong":
            parts.append(
                f"**The Connection**\n\n"
                f"These two developments are tightly linked. "
                f"*\"{title1}\"* and *\"{title2}\"* are part of the same unfolding story, "
                f"with developments in one directly driving the other."
            )
        elif score.confidence == "Moderate":
            parts.append(
                f"**The Connection**\n\n"
                f"There is a meaningful link between these events. "
                f"*\"{title1}\"* and *\"{title2}\"* share underlying factors "
                f"that suggest one is influencing or responding to the other."
            )
        else:
            parts.append(
                f"**The Connection**\n\n"
                f"While not immediately obvious, *\"{title1}\"* and *\"{title2}\"* "
                f"have threads that connect them — common actors, locations, or themes "
                f"that tie these stories together."
            )

        # Shared Entities
        if entity_names:
            variants_info = []
            for e in shared_entities:
                if isinstance(e, dict) and "variants" in e:
                    v = e["variants"]
                    if v[0] != v[1]:
                        variants_info.append(f"{v[0]} / {v[1]}")
                    else:
                        variants_info.append(v[0])
                else:
                    variants_info.append(e.get("text", str(e)) if isinstance(e, dict) else str(e))

            parts.append(
                f"**Key Links**\n\n"
                f"Both events reference: **{', '.join(variants_info[:5])}**. "
                f"These shared references are significant because they point to the same "
                f"actors, regions, or institutions being affected."
            )

        # Impact
        impact_text = []
        if score.embedding_similarity > 0.6:
            impact_text.append(
                "The content of both reports closely mirrors each other, "
                "indicating that multiple sources are tracking the same underlying development "
                "from different angles."
            )
        if score.temporal_proximity > 0.8:
            impact_text.append(
                "The timing is particularly telling — these events occurred within "
                "a very close timeframe, suggesting a direct cause-and-effect relationship "
                "rather than a coincidental overlap."
            )
        if score.source_diversity > 0.5:
            impact_text.append(
                "The fact that different news organizations are reporting on both "
                "adds credibility to the connection."
            )

        if impact_text:
            parts.append(f"**The Impact**\n\n{' '.join(impact_text)}")

        # Bigger Picture
        sentences1 = [s.strip() for s in content1.split('.') if len(s.strip()) > 30][:2]
        sentences2 = [s.strip() for s in content2.split('.') if len(s.strip()) > 30][:2]

        context = ""
        if sentences1:
            context += f"{'. '.join(sentences1)}. "
        if sentences2:
            context += f"Meanwhile, {'. '.join(sentences2).lower()}."

        if context:
            parts.append(f"**The Bigger Picture**\n\n{context}")

        # What to Watch
        parts.append(
            f"**What to Watch**\n\n"
            f"This connected development is worth monitoring closely. "
            f"Official responses and follow-up reporting in the coming hours and days "
            f"will reveal whether this connection deepens or diverges."
        )

        parts.append(f"*Sources: {source1}, {source2}*")

        return "\n\n".join(parts)

    def overview_analysis(self, score: RelationScore, shared_entities: List[dict],
                          article1: dict, article2: dict) -> str:
        """
        Tier 1: Quick overview — 2-3 sentence summary of how two events connect.
        Used as default in both Compare and Probe features.
        """
        title1 = article1.get("title", "Event 1")
        title2 = article2.get("title", "Event 2")
        source1 = article1.get("source", "Unknown")
        source2 = article2.get("source", "Unknown")
        entity_names = [e.get("text", str(e)) for e in shared_entities] if shared_entities else []

        # Connection strength line
        if score.confidence == "Strong":
            link = f"directly linked — both cover the same developing story"
        elif score.confidence == "Moderate":
            link = f"meaningfully connected — one event appears to influence the other"
        elif score.confidence == "Weak":
            link = f"indirectly related — they share common themes or actors"
        else:
            link = f"loosely connected — a potential link worth monitoring"

        overview = f"**{link.capitalize()}.**"

        # Entity bridge
        if entity_names:
            overview += f" Common thread: **{', '.join(entity_names[:3])}**."

        # Timing
        if score.temporal_proximity > 0.8:
            overview += " Occurred close together in time, suggesting cause-and-effect."

        # Sources
        overview += f" *(via {source1} & {source2})*"

        return overview

    def format_probe_summary(self, query_text: str, query_source: str, matches: list, preferred_language: str = "English") -> str:
        """Format prompt for the overall Probe summary synthesis."""
        matches_formatted = []
        for i, m in enumerate(matches):
            art = m["article"]
            if isinstance(art, dict):
                title = art.get("title", "Unknown")
                source = art.get("source", "?")
                score = m.get("score", 0)
            else:
                title = getattr(art, "title", "Unknown")
                source = getattr(art, "source", "?")
                score = m.get("score", 0)
            matches_formatted.append(f"{i+1}. [{source}] {title} (Score: {score:.2f})")
        
        matches_text = "\n".join(matches_formatted) if matches_formatted else "No matches found."

        return PROBE_SUMMARY_PROMPT.format(
            query_text=query_text[:1000],
            query_source=query_source,
            matches_text=matches_text,
            output_language=preferred_language,
        )

    def overview_probe_summary(self, query_text: str, query_source: str,
                                matches: list, probe_entities: list) -> str:
        """
        Generate a concise, conversational intelligence briefing explaining how
        the probe text connects to the existing corpus. Pure prose — no tables, no badges.
        """
        if not matches:
            return "No related articles were found in the corpus for your text."

        strong   = [m for m in matches if m["score"] >= 0.50]
        moderate = [m for m in matches if 0.40 <= m["score"] < 0.50]
        weak     = [m for m in matches if m["score"] < 0.40]

        # Build entity context string
        entity_str = ""
        if probe_entities:
            entity_str = f" Key entities detected: **{', '.join(probe_entities[:5])}**."

        parts = []

        # Opening context
        short_text = query_text[:120] + "…" if len(query_text) > 120 else query_text
        parts.append(f"**Query:** *{short_text}*")
        parts.append("")

        # Intelligence signal headline
        if strong:
            headline = f"**{len(matches)} related articles found — {len(strong)} strongly match your text.**{entity_str}"
        elif moderate:
            headline = f"**{len(matches)} related articles found — {len(moderate)} share meaningful thematic overlap with your text.**{entity_str}"
        else:
            headline = f"**{len(matches)} related articles found — all with weak similarity signals.**{entity_str} Your text may be covering an early or under-represented angle."
        parts.append(headline)
        parts.append("")

        # Connection breakdown — one sentence per article
        parts.append("**How your text connects to existing coverage:**")
        parts.append("")

        for i, m in enumerate(matches, 1):
            article = m["article"]
            if isinstance(article, dict):
                art_title = article.get("title", "Unknown")
                art_source = article.get("source", "?")
            else:
                art_title = getattr(article, "title", "Unknown")
                art_source = getattr(article, "source", "?")

            score_val = m["score"]
            shared = m.get("shared_entities", [])

            if score_val >= 0.50:
                link_desc = "strongly covers the same story"
            elif score_val >= 0.40:
                link_desc = "is meaningfully related"
            else:
                link_desc = "shares a weak thematic thread"

            shared_note = ""
            if shared:
                shared_note = f" (shared context: {', '.join(shared[:3])})"

            parts.append(f"{i}. **{art_source}** — *{art_title[:90]}{'…' if len(art_title) > 90 else ''}* {link_desc}{shared_note}.")

        parts.append("")

        # Closing intelligence note
        if strong:
            parts.append(
                "**Assessment:** Your text is part of an active, multi-source story thread already tracked in the corpus. "
                "Cross-reference the strong matches to understand the full scope of coverage."
            )
        elif moderate:
            parts.append(
                "**Assessment:** Your text introduces a related but distinct angle on an ongoing narrative. "
                "The moderate matches indicate thematic overlap — worth investigating for undercovered dimensions."
            )
        else:
            parts.append(
                "**Assessment:** Your text appears to cover an angle not yet well-represented in the corpus. "
                "These weak signals may indicate an emerging story worth tracking."
            )

        return "\n".join(parts)

class BedrockLLMService(LLMService):
    """
    Amazon Bedrock — 4-Model Strategy

    Model routing:
      - Llama 3.3 70B  → Ask Narad, Situation Room, general fast tasks
                          Best multilingual Indian language support on Bedrock
      - DeepSeek V3.2  → Narrative Conflicts, Cross-Validation
                          Best structured JSON output and reasoning chains
      - Nova Pro       → Multilingual fallback (strongest South Indian lang support)
    """

    def __init__(self):
        import boto3
        self.client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
        self.model_id_llama    = settings.bedrock_model_id_llama      # Llama 3.3 70B
        self.model_id_deepseek = settings.bedrock_model_id_deepseek   # DeepSeek V3.2
        self.model_id_fallback = settings.bedrock_model_id_fallback   # Nova Pro
        # Legacy aliases
        self.model_id_deep = self.model_id_llama
        self.model_id_fast = self.model_id_llama

    # ── Llama 3.3 70B invoke (Ask Narad, Situation Room) ──────────────────
    async def _invoke_llama(self, prompt: str, max_tokens: int = 600) -> str:
        """
        Call Llama 3.3 70B via Bedrock Converse API.
        Handles all Indian languages well (Hindi, Bengali, Marathi, Tamil, etc.)
        Falls back to Nova Pro if unavailable.
        """
        cache_key = llm_cache.make_key("llama33-70b", prompt[:500], str(max_tokens))
        cached = llm_cache.get(cache_key)
        if cached:
            logger.info("LLM cache HIT [llama33-70b] — $0 cost")
            return cached

        if not llm_rate_limiter.check_and_record():
            logger.warning("LLM call BLOCKED by rate limiter [llama33-70b]")
            return None

        try:
            body = json.dumps({
                "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
                "max_gen_len": max_tokens,
                "temperature": 0.4,
                "top_p": 0.9,
            })
            response = self.client.invoke_model(
                modelId=self.model_id_llama, body=body,
                contentType="application/json", accept="application/json",
            )
            result = json.loads(response["body"].read())
            text = result.get("generation", "").strip()
            if text:
                logger.info("Bedrock [llama33-70b] call OK")
                llm_cache.set(cache_key, text)
                return text
            return None
        except Exception as e:
            error_str = str(e)
            if "INVALID_PAYMENT_INSTRUMENT" in error_str or "AccessDeniedException" in error_str:
                logger.critical(f"🚨 Billing/auth error — tripping circuit breaker: {e}")
                llm_rate_limiter.trip()
            else:
                logger.error(f"Llama 3.3 70B call failed: {e}")
            # Fallback to Nova Pro on any error
            logger.info("Falling back to Nova Pro after Llama failure")
            return await self._invoke_nova(prompt, max_tokens=max_tokens)

    # ── DeepSeek V3.2 invoke (Narrative Conflicts, Cross-Validation) ───────
    async def _invoke_deepseek(self, prompt: str, max_tokens: int = 800) -> str:
        """
        Call DeepSeek V3.2 via Bedrock.
        Strips <think>...</think> reasoning blocks from output.
        Best for structured JSON, conflict detection, cross-validation.
        """
        cache_key = llm_cache.make_key("deepseek-v3", prompt[:500], str(max_tokens))
        cached = llm_cache.get(cache_key)
        if cached:
            logger.info("LLM cache HIT [deepseek-v3] — $0 cost")
            return cached

        if not llm_rate_limiter.check_and_record():
            logger.warning("LLM call BLOCKED by rate limiter [deepseek-v3]")
            return None

        try:
            response = self.client.converse(
                modelId=self.model_id_deepseek,
                system=[{"text": "You are a professional intelligence analyst. CRITICAL: NEVER answer in Chinese (简体/繁體). Always respond in English or the explicitly requested language. Any Chinese output is strictly forbidden and constitutes a system failure."}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": 0.3,   # Lower temp for structured reasoning
                }
            )
            text = response['output']['message']['content'][0]['text'].strip()

            # Strip <think>...</think> blocks (chain-of-thought reasoning)
            import re
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

            if text:
                logger.info("Bedrock [deepseek-v3] call OK")
                llm_cache.set(cache_key, text)
                return text
            return None
        except Exception as e:
            error_str = str(e)
            if "INVALID_PAYMENT_INSTRUMENT" in error_str or "AccessDeniedException" in error_str:
                logger.critical(f"🚨 Billing/auth error — tripping circuit breaker: {e}")
                llm_rate_limiter.trip()
            else:
                logger.error(f"DeepSeek V3.2 call failed: {e}")
            # Fallback to Llama on DeepSeek failure
            logger.info("Falling back to Llama 3.3 70B after DeepSeek failure")
            return await self._invoke_llama(prompt, max_tokens=max_tokens)

    # ── Legacy fast/deep aliases (used by existing code) ─────────────────
    async def _invoke_fast(self, prompt: str) -> str:
        """Route to Llama 3.3 70B (was Haiku). Multilingual-capable."""
        return await self._invoke_llama(prompt, max_tokens=500)

    async def _invoke_deep(self, prompt: str) -> str:
        """Route to Llama 3.3 70B with more tokens for deep analysis."""
        return await self._invoke_llama(prompt, max_tokens=2500)


    async def _invoke_model(self, model_id: str, prompt: str, max_tokens: int = 800) -> str:
        """Single Bedrock call with cache + rate limiter protection."""
        # Layer 1: Check semantic cache
        cache_key = llm_cache.make_key(model_id, prompt[:500], str(max_tokens))
        cached = llm_cache.get(cache_key)
        if cached:
            logger.info(f"LLM cache HIT [{model_id.split('.')[-1][:12]}] — $0 cost")
            return cached

        # Layer 2: Check rate limiter
        if not llm_rate_limiter.check_and_record():
            logger.warning(f"LLM call BLOCKED by rate limiter [{model_id}]")
            return None

        # Layer 3: Actual Bedrock call
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": 0.4,
                "messages": [{"role": "user", "content": prompt}],
            })
            response = self.client.invoke_model(
                modelId=model_id, body=body,
                contentType="application/json", accept="application/json",
            )
            result = json.loads(response["body"].read())
            text = result["content"][0]["text"]
            logger.info(f"Bedrock [{model_id.split('.')[-1][:12]}] call OK")

            # Store in cache for future requests
            llm_cache.set(cache_key, text)
            return text
        except Exception as e:
            error_str = str(e)
            # Auto-trip circuit breaker on billing/auth errors
            if "INVALID_PAYMENT_INSTRUMENT" in error_str or "AccessDeniedException" in error_str:
                logger.critical(f"🚨 Billing/auth error — tripping circuit breaker: {e}")
                llm_rate_limiter.trip()
            else:
                logger.error(f"Bedrock call failed [{model_id}]: {e}")
            return None

    async def _invoke_nova(self, prompt: str, max_tokens: int = 800) -> str:
        """Invoke AWS Nova Pro as fallback — with cache + rate limiter."""
        # Layer 1: Check semantic cache
        cache_key = llm_cache.make_key("nova-pro", prompt[:500], str(max_tokens))
        cached = llm_cache.get(cache_key)
        if cached:
            logger.info("Nova Pro cache HIT — $0 cost")
            return cached

        # Layer 2: Check rate limiter
        if not llm_rate_limiter.check_and_record():
            logger.warning("Nova Pro call BLOCKED by rate limiter")
            return None

        try:
            body = json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {
                    "maxTokens": max_tokens,
                    "temperature": 0.4,
                },
            })
            response = self.client.invoke_model(
                modelId=self.model_id_fallback, body=body,
                contentType="application/json", accept="application/json",
            )
            result = json.loads(response["body"].read())
            text = result.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
            if text:
                logger.info("Nova Pro fallback call OK")
                llm_cache.set(cache_key, text)
                return text
            return None
        except Exception as e:
            error_str = str(e)
            if "INVALID_PAYMENT_INSTRUMENT" in error_str or "AccessDeniedException" in error_str:
                logger.critical(f"🚨 Billing error on Nova Pro — tripping circuit breaker: {e}")
                llm_rate_limiter.trip()
            else:
                logger.error(f"Nova Pro fallback failed: {e}")
            return None

    async def generate_probe_summary(
        self, query_text: str, query_source: str, matches: list,
        preferred_language: str = "English"
    ) -> str:
        prompt = self.format_probe_summary(query_text, query_source, matches, preferred_language)
        result = await self._invoke_fast(prompt)
        return result

    async def generate_deep_analysis(
        self, article: dict, entities: list, cluster_info: str,
        preferred_language: str = "English",
    ) -> str:
        prompt = self.format_deep_analysis(article, entities, cluster_info, preferred_language)
        result = await self._invoke_deep(prompt)
        return result or self.fallback_deep_analysis(article, entities, cluster_info)

    async def generate_impact_analysis(
        self, article1: dict, article2: dict, score: RelationScore, shared_entities: List[dict],
        preferred_language: str = "English", detailed: bool = False,
    ) -> str:
        prompt = self.format_impact_analysis(article1, article2, score, shared_entities, preferred_language)
        if detailed:
            result = await self._invoke_deep(prompt)
        else:
            result = await self._invoke_fast(prompt)
        return result or self.fallback_impact_analysis(score, shared_entities, article1, article2)

    async def validate_connection(
        self, article1: dict, article2: dict, score: "RelationScore",
        shared_entities: List[str],
    ) -> str:
        """
        LLM Validation Layer — asks LLM to validate a scored connection.

        Returns: "Valid", "Weak", or "Not Related"
        The LLM never discovers relationships; it only evaluates structured signals.
        """
        prompt = f"""You are a news analysis validator. Your job is to evaluate whether a detected
connection between two news articles is meaningful, based ONLY on the structured signals provided.

Do NOT invent new facts. Evaluate ONLY the data below.

== ARTICLE 1 ==
Title: {article1.get('title', '')}
Source: {article1.get('source', '')}

== ARTICLE 2 ==
Title: {article2.get('title', '')}
Source: {article2.get('source', '')}

== DETECTED SIGNALS ==
Overall score: {score.total_score:.2f}
Embedding similarity: {score.embedding_similarity:.2f}
Entity overlap: {score.entity_overlap:.2f}
Temporal proximity: {score.temporal_proximity:.2f}
Source diversity: {score.source_diversity:.2f}
Shared entities: {', '.join(shared_entities[:10]) if shared_entities else 'None'}

== YOUR TASK ==
Based ONLY on the signals above, respond with exactly one word:
- "Valid" — if the connection appears meaningful (related events, same story, cause-effect)
- "Weak" — if there is some tenuous link but it may be coincidental
- "Not Related" — if the articles appear unrelated despite signal overlap

Respond with ONLY one of: Valid, Weak, Not Related"""

        result = await self._invoke_fast(prompt)
        if result:
            result = result.strip()
            # Parse the LLM response
            r_lower = result.lower()
            if "not related" in r_lower:
                return "Not Related"
            elif "weak" in r_lower:
                return "Weak"
            elif "valid" in r_lower:
                return "Valid"
            # If LLM gave unexpected answer, default to Valid (don't block)
            logger.warning(f"LLM validation returned unexpected: {result[:50]}")
            return "Valid"
        # If LLM call fails entirely, default to Valid (don't block on failure)
        return "Valid"


class MockLLMService(LLMService):
    """Mock service for development — no AWS needed."""

    async def generate_deep_analysis(
        self, article: dict, entities: list, cluster_info: str,
        preferred_language: str = "English",
    ) -> str:
        logger.info(f"Mock LLM: deep analysis [lang={preferred_language}]")
        return self.fallback_deep_analysis(article, entities, cluster_info)

    async def generate_impact_analysis(
        self, article1: dict, article2: dict, score: RelationScore, shared_entities: List[dict],
        preferred_language: str = "English",
    ) -> str:
        logger.info(f"Mock LLM: impact analysis [lang={preferred_language}]")
        return self.fallback_impact_analysis(score, shared_entities, article1, article2)

    async def generate_probe_summary(
        self, query_text: str, query_source: str, matches: list,
        preferred_language: str = "English"
    ) -> str:
        logger.info(f"Mock LLM: probe summary [lang={preferred_language}]")
        return "Mock analysis summary for probe feature."

    async def validate_connection(
        self, article1: dict, article2: dict, score: "RelationScore",
        shared_entities: List[str],
    ) -> str:
        """Mock validation — always returns Valid."""
        if score.total_score >= 0.55:
            return "Valid"
        elif score.total_score >= 0.40:
            return "Weak"
        return "Not Related"


def get_llm_service() -> LLMService:
    """Factory — returns the configured LLM backend."""
    if settings.llm_backend == "bedrock":
        return BedrockLLMService()
    return MockLLMService()

