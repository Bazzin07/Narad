const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Response types matching backend schemas ─────────────────────────

export interface ArticleSummary {
    id: string;
    title: string;
    source: string;
    published_at: string;
    language: string;
    entities: string[];
    cluster_id: number | null;
    image_url: string | null;
    topic: string | null;
}

export interface ArticleDetail {
    id: string;
    title: string;
    content: string;
    summary: string | null;
    source: string;
    url: string;
    published_at: string;
    language: string;
    entities: Array<{ text: string; type: string }>;
    cluster_id: number | null;
    processed: number;
    image_url: string | null;
    topic: string | null;
}

export interface TopicCount {
    topic: string;
    count: number;
}

export interface RelationScore {
    total_score: number;
    confidence: string;
    embedding_similarity: number;
    entity_overlap: number;
    temporal_proximity: number;
    source_diversity: number;
    graph_distance: number;
    credibility_factor: number;
}

export interface ProbeMatch {
    article: ArticleSummary;
    relation_score: RelationScore;
    shared_entities: string[];
    explanation: string | null;
}

export interface ProbeResponse {
    query_text: string;
    query_source: string;
    detected_language: string;
    extracted_entities: string[];
    matches: ProbeMatch[];
    total_matches_found: number;
    overview_map: string | null;
    analysis_summary: string | null;
}

export interface CompareResponse {
    article1: ArticleSummary;
    article2: ArticleSummary;
    relation_score: RelationScore;
    shared_entities: string[];
    overview: string | null;
    explanation: string | null;
}

// ── Fetchers ─────────────────────────────────────────────────────────

const DEFAULT_TIMEOUT_MS = 15_000; // 15 second timeout (generous for cold starts)
const MAX_RETRIES = 2; // retry up to 2 times (3 total attempts)

async function apiFetch<T>(
    path: string,
    options?: RequestInit & { timeoutMs?: number; retries?: number },
): Promise<T> {
    const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    const maxRetries = options?.retries ?? MAX_RETRIES;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);

        try {
            const res = await fetch(`${API_BASE}${path}`, {
                ...options,
                signal: controller.signal,
                headers: {
                    "Content-Type": "application/json",
                    ...options?.headers,
                },
            });
            clearTimeout(timer);

            if (!res.ok) {
                throw new Error(`API error: ${res.status} ${res.statusText}`);
            }
            return await res.json();
        } catch (err: unknown) {
            clearTimeout(timer);
            lastError = err instanceof Error ? err : new Error(String(err));

            // Silently handle AbortError (timeout) — don't let it pollute console
            const isAbort = lastError.name === "AbortError" ||
                lastError.message.includes("abort");

            // Don't retry on 4xx client errors (except 408/429)
            if (lastError.message.includes("API error: 4") &&
                !lastError.message.includes("408") &&
                !lastError.message.includes("429")) {
                throw lastError;
            }

            // Wait before retry with exponential backoff
            if (attempt < maxRetries) {
                const backoffMs = isAbort ? 1000 * (attempt + 1) : 500 * (attempt + 1);
                await new Promise((r) => setTimeout(r, backoffMs));
            }
        }
    }

    // For abort errors, throw a cleaner message without triggering console noise
    if (lastError && (lastError.name === "AbortError" || lastError.message.includes("abort"))) {
        throw new Error("Request timed out. The server may be busy.");
    }
    throw lastError ?? new Error("Request failed after retries");
}

export async function getArticles(params?: {
    limit?: number;
    offset?: number;
    language?: string;
    region?: string;
}): Promise<ArticleSummary[]> {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));
    if (params?.language) query.set("language", params.language);
    if (params?.region) query.set("region", params.region);
    const qs = query.toString();
    return apiFetch<ArticleSummary[]>(`/api/news${qs ? `?${qs}` : ""}`);
}

export async function getArticle(id: string): Promise<ArticleDetail> {
    return apiFetch<ArticleDetail>(`/api/news/${id}`);
}

export async function getTopics(): Promise<{ topics: TopicCount[] }> {
    return apiFetch<{ topics: TopicCount[] }>("/api/topics");
}

export async function getTopicArticles(
    topic: string,
    limit?: number
): Promise<ArticleSummary[]> {
    const qs = limit ? `?limit=${limit}` : "";
    const data = await apiFetch<{ articles: ArticleSummary[] }>(
        `/api/topics/${topic}${qs}`
    );
    return data.articles;
}

export async function probe(
    text: string,
    source?: string,
    detailed?: boolean
): Promise<ProbeResponse> {
    return apiFetch<ProbeResponse>("/api/probe", {
        method: "POST",
        body: JSON.stringify({
            text,
            source: source || "narad-frontend",
            detailed: detailed || false,
        }),
    });
}

export async function compare(
    article1Id: string,
    article2Id: string,
    detailed?: boolean
): Promise<CompareResponse> {
    return apiFetch<CompareResponse>("/api/compare", {
        method: "POST",
        body: JSON.stringify({
            article1_id: article1Id,
            article2_id: article2Id,
            session_id: `narad-ui-${Date.now()}`,
            detailed: detailed || false,
        }),
    });
}



export interface DeepAnalysis {
    article_id: string;
    analysis: string;
    session_id: string;
}

export async function analyzeArticle(
    articleId: string,
    sessionId?: string
): Promise<DeepAnalysis> {
    const sid = sessionId || `narad-ui-${Date.now()}`;
    return apiFetch<DeepAnalysis>(
        `/api/news/${articleId}/analyze?session_id=${sid}`,
        { method: "POST" }
    );
}

export async function getClusters(): Promise<unknown> {
    return apiFetch<unknown>("/api/clusters");
}

// ── Event Intelligence (Explore Connections) ─────────────────────────

export interface ExploreRelatedEvent {
    id: string;
    title: string;
    source: string;
    topic: string;
    published_at: string;
    image_url: string | null;
    relevance_score: number;
    connection_type: string;
    shared_entities: string[];
    domain_transition: string | null;
}

export interface ExploreConfidence {
    level: string;  // "Strong" | "Moderate" | "Speculative"
    score: number;
    description: string;
    metrics?: {
        avg_relevance: number;
        max_relevance: number;
        cross_domain_links: number;
        entity_linked_events: number;
    };
}

export interface ExploreResponse {
    seed_article: {
        id: string;
        title: string;
        source: string;
        topic: string;
        published_at: string;
    };
    related_events: ExploreRelatedEvent[];
    narrative: string;
    confidence: ExploreConfidence;
    signals_summary: {
        total_events: number;
        domains_covered: string[];
        connection_breakdown: Record<string, number>;
        domain_transitions?: string[];
        key_entities?: string[];
        dominant_pattern?: string;
    };
    total_candidates_scanned: number;
    total_relevant: number;
}

export async function exploreConnections(
    articleId: string,
): Promise<ExploreResponse> {
    return apiFetch<ExploreResponse>(
        `/api/news/${articleId}/explore`,
        { method: "POST", timeoutMs: 20_000, retries: 1 }
    );
}

// ── Multi-Source Fact Sheet ───────────────────────────────────────────

export interface FactSheetCoverage {
    total_sources: number;
    total_articles: number;
    languages: string[];
    date_range: { earliest: string; latest: string };
}

export interface FactSheetEntity {
    name: string;
    mentioned_in: number;
    total_sources: number;
}

export interface FactSheetPerspective {
    source: string;
    language: string;
    title: string;
    angle: string;
    published_at: string;
}

export interface FactSheetArticle {
    id: string;
    title: string;
    source: string;
    language: string;
    published_at: string;
    relevance_score: number;
    shared_entities: string[];
    url: string;
}

export interface FactSheetResponse {
    seed_article: {
        id: string;
        title: string;
        source: string;
        language: string;
        published_at: string;
        topic: string;
        url: string;
    };
    coverage: FactSheetCoverage;
    key_entities: FactSheetEntity[];
    source_perspectives: FactSheetPerspective[];
    timeline: Array<{ source: string; title: string; published_at: string; language: string }>;
    narrative: string;
    related_articles: FactSheetArticle[];
}

export async function getFactSheet(
    articleId: string,
): Promise<FactSheetResponse> {
    return apiFetch<FactSheetResponse>(
        `/api/news/${articleId}/fact-sheet`,
        { timeoutMs: 20_000, retries: 1 }
    );
}

// ── Source Health Monitor ─────────────────────────────────────────────

export interface SourceHealth {
    id: string;
    name: string;
    base_url: string;
    source_type: string;
    language: string;
    source_region: string;
    active: boolean;
    status: "healthy" | "degraded" | "failing" | "disabled" | "stale" | "unknown";
    last_fetched_at: string | null;
    last_success_at: string | null;
    consecutive_failures: number;
    total_fetches: number;
    total_articles_fetched: number;
    articles_last_24h: number;
}

export interface SourceHealthSummary {
    total_sources: number;
    healthy: number;
    degraded: number;
    failing: number;
    disabled: number;
    stale: number;
    unknown: number;
}

export interface SourceHealthResponse {
    summary: SourceHealthSummary;
    sources: SourceHealth[];
}

export async function getSourceHealth(): Promise<SourceHealthResponse> {
    return apiFetch<SourceHealthResponse>("/api/sources/health");
}

export async function enableSource(sourceId: string): Promise<{ message: string }> {
    return apiFetch<{ message: string }>(`/api/sources/${sourceId}/enable`, { method: "POST" });
}

export async function disableSource(sourceId: string): Promise<{ message: string }> {
    return apiFetch<{ message: string }>(`/api/sources/${sourceId}/disable`, { method: "POST" });
}

// ── Analytics: Timeline ──────────────────────────────────────────────

export interface TimelineEvent {
    id: string;
    title: string;
    source: string;
    published_at: string;
    topic: string;
    sentiment: number | null;
    key_entities: string[];
    summary: string;
    image_url: string | null;
    similarity: number;
    is_seed?: boolean;
}

export interface TimelineResponse {
    seed: { id: string; title: string; source: string; published_at: string };
    timeline: TimelineEvent[];
    total_events: number;
}

export async function getTimeline(articleId: string): Promise<TimelineResponse> {
    return apiFetch<TimelineResponse>(
        `/api/analytics/timeline/${articleId}`,
        { timeoutMs: 15_000, retries: 1 }
    );
}



// ── Analytics: Sentiment Trends ──────────────────────────────────────

export interface SentimentPoint {
    date: string;
    sentiment: number;
    count: number;
}

export interface SentimentTopicResponse {
    topic: string;
    days: number;
    india_trend: SentimentPoint[];
    global_trend: SentimentPoint[];
}

export interface SentimentEntityResponse {
    entity: string;
    days: number;
    trend: SentimentPoint[];
}

export async function getSentimentByTopic(
    topic: string,
    days: number = 7
): Promise<SentimentTopicResponse> {
    return apiFetch<SentimentTopicResponse>(
        `/api/analytics/sentiment/topic/${topic}?days=${days}`
    );
}

export async function getSentimentByEntity(
    entityName: string,
    days: number = 7
): Promise<SentimentEntityResponse> {
    return apiFetch<SentimentEntityResponse>(
        `/api/analytics/sentiment/entity/${encodeURIComponent(entityName)}?days=${days}`
    );
}

// ── Analytics: Source Bias Analysis ──────────────────────────────────

export interface BiasComparison {
    id: string;
    title: string;
    source: string;
    language: string;
    published_at: string;
    sentiment: number;
    sentiment_label: string;
    key_entities: string[];
    similarity: number;
}

export interface BiasAnalysisResponse {
    seed: {
        id: string;
        title: string;
        source: string;
        sentiment: number | null;
        key_entities: string[];
    };
    comparisons: BiasComparison[];
    narrative: string;
    total_sources: number;
}

export async function getBiasAnalysis(articleId: string): Promise<BiasAnalysisResponse> {
    return apiFetch<BiasAnalysisResponse>(
        `/api/analytics/bias/${articleId}`,
        { method: "POST", timeoutMs: 20_000, retries: 1 }
    );
}

// ── Dashboard: India Command Center ─────────────────────────────────

export interface StateHeatmapEntry {
    state: string;
    article_count: number;
    avg_sentiment: number;
    info: Record<string, string>;
}

export interface StateAnalytics {
    state: string;
    info: Record<string, string>;
    article_count: number;
    avg_sentiment: number;
    topic_distribution: Array<{ topic: string; count: number }>;
    top_sources: Array<{ source: string; count: number }>;
}

export interface DashboardNewsItem {
    id: string;
    title: string;
    source: string;
    published_at: string | null;
    sentiment_score: number | null;
    state: string | null;
    topic: string | null;
    image_url: string | null;
    url: string;
}

export interface AIBriefingResponse {
    state: string;
    info: Record<string, string>;
    briefing: string;
    source: string;
    article_count: number;
}

export interface MarketData {
    sensex: number | null;
    sensex_prev: number | null;
    nifty: number | null;
    nifty_prev: number | null;
    rupee_usd: number | null;
    eur_inr: number | null;
    gbp_inr: number | null;
    gold: number | null;
    gold_prev: number | null;
    crude_oil: number | null;
    crude_oil_prev: number | null;
    silver: number | null;
    silver_prev: number | null;
    natural_gas: number | null;
    natural_gas_prev: number | null;
    updated_at: string;
}

export interface MapMarker {
    id: string;
    name: string;
    coordinates: [number, number]; // [longitude, latitude]
    state: string;
    info: string;
}

export async function getMapMarkers(type: string): Promise<{ markers: MapMarker[] }> {
    return apiFetch<{ markers: MapMarker[] }>(`/api/dashboard/map-markers?type=${type}`);
}

export async function getDashboardHeatmap(): Promise<{ states: StateHeatmapEntry[]; total_states: number }> {
    return apiFetch(`/api/dashboard/heatmap`);
}

export async function getStateAnalytics(state: string): Promise<StateAnalytics> {
    return apiFetch(`/api/dashboard/state/${state}`);
}

export interface RegionalAnalyticsResponse {
    tech: {
        ai_growth: string;
        funding: string;
        sparkline: number[];
    };
    political: {
        sentiment_index: string;
        sentiment_value: number;
        top_policies: string[];
    };
    societal: {
        migration_rate: string;
        sparkline: number[];
    };
}

export async function getDashboardNews(state?: string, limit = 20): Promise<DashboardNewsItem[]> {
    const params = new URLSearchParams();
    if (state) params.set("state", state);
    params.set("limit", String(limit));
    return apiFetch(`/api/dashboard/news?${params.toString()}`);
}

export async function getRegionalAnalytics(state: string | null): Promise<RegionalAnalyticsResponse> {
    const qs = state ? `?state=${encodeURIComponent(state)}` : "";
    return apiFetch(`/api/dashboard/regional-analytics${qs}`);
}

export async function getAIBriefing(state: string): Promise<AIBriefingResponse> {
    return apiFetch(`/api/dashboard/briefing/${state}`, { method: "POST", timeoutMs: 15_000 });
}

export async function getMarketData(): Promise<MarketData> {
    return apiFetch(`/api/dashboard/markets`);
}

export async function getStateData(): Promise<Record<string, Record<string, string>>> {
    return apiFetch(`/api/dashboard/state-data`);
}

// ── New GenAI Command Center APIs ────────────────────────────────────────────

export interface DomainRadarResponse {
    state: string;
    domains: Record<string, { sentiment: number; article_count: number }>;
}

export interface SituationRoomResponse {
    briefing: string;
    articles_used: number;
    source: string;
}

export interface NarrativeConflict {
    article_a: { id: string; title: string; source: string; sentiment: number };
    article_b: { id: string; title: string; source: string; sentiment: number };
    sentiment_delta: number;
    similarity: number;
    explanation: string;
}

export interface NarrativeConflictsResponse {
    conflicts: NarrativeConflict[];
    total: number;
}

export interface AskNaradSource {
    id: string;
    title: string;
    source: string;
    url: string;
    published_at: string;
    relevance_score: number;
}

export interface AskNaradResponse {
    answer: string;
    sources: AskNaradSource[];
    pages_retrieved: number;
    articles_scanned: number;
    source: string;
}

export async function getDomainRadar(state: string | null): Promise<DomainRadarResponse> {
    const qs = state ? `?state=${encodeURIComponent(state)}` : "";
    return apiFetch(`/api/dashboard/domain-radar${qs}`);
}

export async function getSituationRoom(state: string | null): Promise<SituationRoomResponse> {
    const qs = state ? `?state=${encodeURIComponent(state)}` : "";
    return apiFetch(`/api/dashboard/situation-room${qs}`, { method: "POST", timeoutMs: 60_000 });
}

export async function getNarrativeConflicts(state: string | null): Promise<NarrativeConflictsResponse> {
    const qs = state ? `?state=${encodeURIComponent(state)}` : "";
    return apiFetch(`/api/dashboard/narrative-conflicts${qs}`);
}

export async function askNarad(question: string, state: string | null, detailed = false): Promise<AskNaradResponse> {
    return apiFetch(`/api/dashboard/ask`, {
        method: "POST",
        body: JSON.stringify({ question, state, detailed }),
        timeoutMs: 60_000,
    });
}
