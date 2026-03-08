"use client";

import { useState, useEffect, use } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import ClientShell from "../../components/ClientShell";
import { getArticle, analyzeArticle, exploreConnections, getFactSheet, type ArticleDetail, type ExploreResponse, type FactSheetResponse } from "../../lib/api";
import { TimelinePanel, BiasAnalysisPanel } from "../../components/AnalyticsPanels";

// Filter out garbage entities (YouTube channels, boilerplate, transliterated noise)
function filterEntities(entities: { text: string; type: string }[]) {
    const garbage = new Set([
        "subscribe", "youtube channel", "live tv", "breaking news",
        "abp news", "abp", "star news", "hindi news channel",
        "breaking hindi news", "aapko rakhe aagey", "aapko rakhe aagey'", "hmlaa",
        "abp hindi", "hindi", "abp news abp news", "hindi, sports news",
        "ko ttaargett", "hindii smaacaar", "hinsdii smaacaar",
        "taajaa khbr", "hmale kaa", "hmle kaa", "hiNdii smaacaar",
        "breaking stories", "live news", "news channel",
    ]);
    return entities.filter((e) => {
        const lower = e.text.toLowerCase().trim();
        if (garbage.has(lower)) return false;
        if (lower.length < 2 || lower.length > 60) return false;
        // Skip transliterated noise (mixed-case Latin with no spaces, NER junk)
        if (/^[a-zA-Z]{2,}$/.test(e.text.trim()) && !e.text.includes(" ")) return false;
        // Skip entities that are just URLs or hashtags
        if (lower.startsWith("http") || lower.startsWith("#")) return false;
        // Skip common news/media noise patterns
        if (/youtube|subscribe|channel|follow|watch|live\s*(tv|news)|breaking|sports\s*news/i.test(lower)) return false;
        // Skip transliterated Hindi noise (lowercase with double letters, mixed case)
        if (/^[a-z\s]{2,}$/.test(lower) && /(.)\1/.test(lower) && lower.length < 15) return false;
        // Skip entities containing "news" as standalone word
        if (/\bnews\b/i.test(lower) && lower.length < 30) return false;
        return true;
    });
}

// Generate a clean overview from article content
function generateOverview(content: string, title: string): string {
    if (!content || content.length < 30) return title;
    // Split into sentences, take first 3-4 meaningful ones
    const sentences = content
        .split(/[.।!?]+/)
        .map((s) => s.trim())
        .filter((s) => s.length > 25 && s.length < 500);
    if (sentences.length === 0) return content.slice(0, 300);
    return sentences.slice(0, 3).join(". ") + ".";
}

export default function ArticlePage({ params }: { params: Promise<{ id: string }> }) {
    const resolvedParams = use(params);
    const [language, setLanguage] = useState("all");
    const [article, setArticle] = useState<ArticleDetail | null>(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [analysis, setAnalysis] = useState<string | null>(null);
    const [analyzing, setAnalyzing] = useState(false);
    const [analysisError, setAnalysisError] = useState("");
    const [explore, setExplore] = useState<ExploreResponse | null>(null);
    const [exploring, setExploring] = useState(false);
    const [exploreError, setExploreError] = useState("");
    const [factSheet, setFactSheet] = useState<FactSheetResponse | null>(null);
    const [loadingFactSheet, setLoadingFactSheet] = useState(false);
    const [factSheetError, setFactSheetError] = useState("");

    useEffect(() => {
        async function loadArticle() {
            setLoading(true);
            try {
                const art = await getArticle(resolvedParams.id);
                setArticle(art);
            } catch (err) {
                setError("Article not found");
                console.error(err);
            }
            setLoading(false);
        }
        loadArticle();
    }, [resolvedParams.id]);



    if (loading) {
        return (
            <ClientShell language={language} onLanguageChange={setLanguage}>
                <div style={{ padding: "4rem var(--page-gutter)" }}>
                    <div className="max-w-5xl">
                        <div className="h-3 w-32 mb-4 animate-pulse" style={{ background: "var(--bg-surface)" }} />
                        <div className="h-8 w-full mb-2 animate-pulse" style={{ background: "var(--bg-surface)" }} />
                        <div className="h-8 w-3/4 mb-6 animate-pulse" style={{ background: "var(--bg-surface)" }} />
                        <div className="h-48 w-full mb-6 animate-pulse" style={{ background: "var(--bg-surface)" }} />
                        <div className="h-4 w-full mb-2 animate-pulse" style={{ background: "var(--bg-surface)" }} />
                        <div className="h-4 w-full mb-2 animate-pulse" style={{ background: "var(--bg-surface)" }} />
                        <div className="h-4 w-2/3 animate-pulse" style={{ background: "var(--bg-surface)" }} />
                    </div>
                </div>
            </ClientShell>
        );
    }

    if (error || !article) {
        return (
            <ClientShell language={language} onLanguageChange={setLanguage}>
                <div style={{ padding: "4rem var(--page-gutter)" }}>
                    <p style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>{error || "Not found"}</p>
                    <Link href="/" style={{ color: "var(--accent)", fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
                        ← Back to feed
                    </Link>
                </div>
            </ClientShell>
        );
    }

    const cleanEntities = filterEntities(article.entities || []);
    const overview = generateOverview(article.content, article.title);

    return (
        <ClientShell language={language} onLanguageChange={setLanguage}>
            <div style={{ padding: "2rem var(--page-gutter) 4rem" }}>
                {/* Back link */}
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6">
                    <Link
                        href="/"
                        className="no-underline inline-flex items-center gap-2 transition-colors"
                        style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.7rem",
                            color: "var(--text-muted)",
                            textDecoration: "none",
                        }}
                    >
                        <span>←</span> BACK TO FEED
                    </Link>
                </motion.div>

                {/* Hero */}
                <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="max-w-5xl mb-8"
                >
                    {/* Meta bar */}
                    <div className="flex items-center gap-3 mb-4 flex-wrap">
                        <span
                            style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "0.65rem",
                                letterSpacing: "0.05em",
                                color: "var(--text-muted)",
                            }}
                        >
                            {article.source}
                        </span>
                        <span style={{ color: "var(--text-dim)" }}>·</span>
                        {article.published_at && (
                            <time
                                style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: "0.6rem",
                                    color: "var(--text-dim)",
                                }}
                            >
                                {new Date(article.published_at).toLocaleString("en-IN", {
                                    dateStyle: "long",
                                    timeStyle: "short",
                                })}
                            </time>
                        )}
                        {article.topic && article.topic !== "general" && (
                            <>
                                <span style={{ color: "var(--text-dim)" }}>·</span>
                                <span
                                    className="inline-block px-2 py-0.5"
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: "0.55rem",
                                        letterSpacing: "0.08em",
                                        textTransform: "uppercase",
                                        color: "var(--accent)",
                                        border: "1px solid var(--border-accent)",
                                        background: "var(--accent-dim)",
                                    }}
                                >
                                    {article.topic}
                                </span>
                            </>
                        )}
                    </div>

                    {/* Title */}
                    <h1
                        className="m-0 mb-4"
                        style={{
                            fontFamily: "var(--font-headline)",
                            fontSize: "clamp(1.8rem, 3.5vw, 2.8rem)",
                            fontWeight: 600,
                            lineHeight: 1.15,
                        }}
                    >
                        {article.title}
                    </h1>
                </motion.div>

                {/* Article image */}
                {article.image_url && (
                    <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        className="max-w-5xl mb-8"
                    >
                        <img
                            src={article.image_url}
                            alt={article.title}
                            style={{
                                width: "100%",
                                maxHeight: "420px",
                                objectFit: "cover",
                                border: "1px solid var(--border-subtle)",
                            }}
                            onError={(e) => {
                                (e.target as HTMLImageElement).style.display = "none";
                            }}
                        />
                    </motion.div>
                )}

                {/* Overview Section */}
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 }}
                    className="max-w-5xl mb-10"
                >
                    <div className="flex items-center gap-2 mb-4">
                        <div
                            style={{
                                width: "3px",
                                height: "16px",
                                background: "var(--text-primary)",
                            }}
                        />
                        <span
                            style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "0.7rem",
                                letterSpacing: "0.1em",
                                textTransform: "uppercase",
                                color: "var(--text-primary)",
                                fontWeight: 600,
                            }}
                        >
                            Overview
                        </span>
                    </div>
                    <p
                        style={{
                            fontFamily: "var(--font-body)",
                            fontSize: "1rem",
                            lineHeight: 1.8,
                            color: "var(--text-secondary)",
                            margin: 0,
                        }}
                    >
                        {overview}
                    </p>

                    {/* Clean entities as subtle tags */}
                    {cleanEntities.length > 0 && (
                        <div className="mt-5 flex flex-wrap gap-2">
                            {cleanEntities.slice(0, 8).map((ent, i) => (
                                <span
                                    key={i}
                                    className="px-2 py-0.5"
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: "0.58rem",
                                        color: "var(--text-muted)",
                                        border: "1px solid var(--border-subtle)",
                                        background: "var(--bg-surface)",
                                        letterSpacing: "0.03em",
                                    }}
                                >
                                    {ent.text}
                                </span>
                            ))}
                        </div>
                    )}
                </motion.div>

                {/* Separator */}
                <div className="separator mb-8 max-w-5xl" />

                {/* Action Buttons Section */}
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25 }}
                    className="max-w-5xl mb-12"
                >
                    {/* Button row */}
                    {!analysis && !analyzing && !explore && !exploring && (
                        <div className="flex items-center gap-3 flex-wrap">
                            <button
                                onClick={async () => {
                                    setAnalyzing(true);
                                    setAnalysisError("");
                                    try {
                                        const result = await analyzeArticle(resolvedParams.id);
                                        setAnalysis(result.analysis);
                                    } catch (err) {
                                        console.error(err);
                                        setAnalysisError("Analysis unavailable. Try again later.");
                                    }
                                    setAnalyzing(false);
                                }}
                                className="cursor-pointer transition-all duration-200"
                                style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: "0.7rem",
                                    letterSpacing: "0.08em",
                                    textTransform: "uppercase",
                                    color: "var(--accent)",
                                    background: "transparent",
                                    border: "1px solid var(--accent)",
                                    padding: "10px 24px",
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: "10px",
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = "var(--accent)";
                                    e.currentTarget.style.color = "#fff";
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = "transparent";
                                    e.currentTarget.style.color = "var(--accent)";
                                }}
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
                                </svg>
                                Deep Analysis
                            </button>

                            <button
                                onClick={async () => {
                                    setExploring(true);
                                    setExploreError("");
                                    try {
                                        const result = await exploreConnections(resolvedParams.id);
                                        setExplore(result);
                                    } catch (err) {
                                        console.error(err);
                                        setExploreError("Connection analysis unavailable. Try again later.");
                                    }
                                    setExploring(false);
                                }}
                                className="cursor-pointer transition-all duration-200"
                                style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: "0.7rem",
                                    letterSpacing: "0.08em",
                                    textTransform: "uppercase",
                                    color: "var(--accent)",
                                    background: "transparent",
                                    border: "1px solid var(--accent)",
                                    padding: "10px 24px",
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: "10px",
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = "var(--accent)";
                                    e.currentTarget.style.color = "#fff";
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = "transparent";
                                    e.currentTarget.style.color = "var(--accent)";
                                }}
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /><circle cx="5" cy="12" r="1" />
                                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                                </svg>
                                Explore Connections
                            </button>

                            {/* Fact Sheet Button */}
                            <button
                                onClick={async () => {
                                    setLoadingFactSheet(true);
                                    setFactSheetError("");
                                    try {
                                        const result = await getFactSheet(resolvedParams.id);
                                        setFactSheet(result);
                                    } catch (err) {
                                        setFactSheetError(err instanceof Error ? err.message : "Failed to generate fact sheet");
                                    } finally {
                                        setLoadingFactSheet(false);
                                    }
                                }}
                                disabled={loadingFactSheet || !!factSheet}
                                className="cursor-pointer transition-all duration-200"
                                style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: "0.7rem",
                                    letterSpacing: "0.08em",
                                    textTransform: "uppercase",
                                    color: factSheet ? "#628DD3" : "var(--accent)",
                                    background: "transparent",
                                    border: `1px solid ${factSheet ? "#628DD3" : "var(--accent)"}`,
                                    padding: "10px 24px",
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: "10px",
                                    opacity: loadingFactSheet ? 0.6 : 1,
                                }}
                                onMouseEnter={(e) => {
                                    if (!factSheet) {
                                        e.currentTarget.style.background = "var(--accent)";
                                        e.currentTarget.style.color = "#fff";
                                    }
                                }}
                                onMouseLeave={(e) => {
                                    if (!factSheet) {
                                        e.currentTarget.style.background = "transparent";
                                        e.currentTarget.style.color = "var(--accent)";
                                    }
                                }}
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                    <polyline points="14 2 14 8 20 8" />
                                    <line x1="16" y1="13" x2="8" y2="13" />
                                    <line x1="16" y1="17" x2="8" y2="17" />
                                </svg>
                                {loadingFactSheet ? "Generating..." : factSheet ? "✓ Fact Sheet Ready" : "Fact Sheet"}
                            </button>
                        </div>
                    )}

                    {/* Fact Sheet Error */}
                    {factSheetError && (
                        <div style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", color: "#dc2626", fontSize: "0.85rem" }}>
                            {factSheetError}
                        </div>
                    )}

                    {/* Fact Sheet Loading */}
                    {loadingFactSheet && (
                        <div className="p-6" style={{ border: "1px solid var(--border-accent)", background: "var(--accent-dim)" }}>
                            <div className="flex items-center gap-3 mb-4">
                                <div className="live-dot" style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--accent)" }} />
                                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--accent)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                                    Building multi-source fact sheet...
                                </span>
                            </div>
                            <div className="space-y-2" style={{ fontFamily: "var(--font-mono)", fontSize: "0.6rem", color: "var(--text-muted)" }}>
                                <p>→ Searching for same-event coverage across sources</p>
                                <p>→ Comparing perspectives across languages</p>
                                <p>→ Consolidating facts and entities</p>
                            </div>
                        </div>
                    )}

                    {/* Fact Sheet Results */}
                    {factSheet && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            style={{ border: "1px solid var(--border-accent)", borderRadius: "8px", overflow: "hidden", background: "var(--bg-elevated)" }}
                        >
                            {/* Header */}
                            <div style={{ background: "var(--accent-dim)", padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--accent)", fontWeight: 600 }}>
                                        Multi-Source Fact Sheet
                                    </span>
                                </div>
                                <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
                                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-primary)" }}>
                                        {factSheet.coverage.total_sources} sources
                                    </span>
                                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-primary)" }}>
                                        {factSheet.coverage.total_articles} articles
                                    </span>
                                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-primary)" }}>
                                        {factSheet.coverage.languages.join(", ").toUpperCase()}
                                    </span>
                                </div>
                            </div>

                            {/* Key Entities */}
                            {factSheet.key_entities.length > 0 && (
                                <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)" }}>
                                    <h4 style={{ fontFamily: "var(--font-mono)", fontSize: "0.6rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "8px" }}>
                                        Key Entities
                                    </h4>
                                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                                        {factSheet.key_entities.slice(0, 10).map((entity, i) => (
                                            <span key={i} style={{
                                                padding: "3px 10px", borderRadius: "999px", fontSize: "0.75rem",
                                                background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)",
                                            }}>
                                                {entity.name} <span style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>×{entity.mentioned_in}</span>
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Source Perspectives */}
                            {factSheet.source_perspectives.length > 0 && (
                                <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)" }}>
                                    <h4 style={{ fontFamily: "var(--font-mono)", fontSize: "0.6rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "12px" }}>
                                        Source Perspectives ({factSheet.source_perspectives.length})
                                    </h4>
                                    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                                        {factSheet.source_perspectives.map((p, i) => (
                                            <div key={i} style={{ padding: "10px 14px", background: "var(--bg-surface)", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
                                                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                                                    <span style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>{p.source}</span>
                                                    <span style={{ fontSize: "0.65rem", padding: "1px 6px", borderRadius: "4px", background: "var(--accent-dim)", color: "var(--accent)" }}>
                                                        {p.language.toUpperCase()}
                                                    </span>
                                                </div>
                                                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>{p.title}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Narrative */}
                            <div style={{ padding: "20px", background: "#fff" }}>
                                <h4 style={{ fontFamily: "var(--font-mono)", fontSize: "0.6rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "12px" }}>
                                    Consolidated Analysis
                                </h4>
                                <div
                                    style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "#374151" }}
                                    dangerouslySetInnerHTML={{
                                        __html: factSheet.narrative
                                            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                            .replace(/##\s*(.*?)(?:\n|$)/g, '<h5 style="margin:12px 0 4px;font-size:0.85rem;color:#1e293b">$1</h5>')
                                            .replace(/\n- /g, '<br/>• ')
                                            .replace(/\n/g, '<br/>')
                                    }}
                                />
                            </div>
                        </motion.div>
                    )}

                    {/* Deep Analysis loading */}
                    {analyzing && (
                        <div className="p-6" style={{ border: "1px solid var(--border-subtle)" }}>
                            <div className="flex items-center gap-3 mb-4">
                                <div className="live-dot" style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--text-primary)" }} />
                                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-muted)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                                    Generating analysis...
                                </span>
                            </div>
                            <div className="space-y-3">
                                <div className="h-3 w-full animate-pulse" style={{ background: "var(--bg-surface)" }} />
                                <div className="h-3 w-11/12 animate-pulse" style={{ background: "var(--bg-surface)" }} />
                                <div className="h-3 w-4/5 animate-pulse" style={{ background: "var(--bg-surface)" }} />
                                <div className="h-3 w-3/5 animate-pulse" style={{ background: "var(--bg-surface)" }} />
                            </div>
                        </div>
                    )}

                    {/* Explore loading */}
                    {exploring && (
                        <div className="p-6" style={{ border: "1px solid var(--border-accent, #e85d5d33)", background: "var(--accent-dim)" }}>
                            <div className="flex items-center gap-3 mb-4">
                                <div className="live-dot" style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--accent)" }} />
                                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--accent)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                                    Scanning event network...
                                </span>
                            </div>
                            <div className="space-y-2" style={{ fontFamily: "var(--font-mono)", fontSize: "0.6rem", color: "var(--text-muted)" }}>
                                <p>→ Searching vector space for related events</p>
                                <p>→ Analyzing entity overlap and temporal signals</p>
                                <p>→ Detecting cross-domain patterns</p>
                                <p>→ Generating narrative...</p>
                            </div>
                            <div className="mt-4 space-y-2">
                                <div className="h-3 w-full animate-pulse" style={{ background: "var(--bg-surface)" }} />
                                <div className="h-3 w-4/5 animate-pulse" style={{ background: "var(--bg-surface)" }} />
                            </div>
                        </div>
                    )}

                    {analysisError && (
                        <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "8px" }}>{analysisError}</p>
                    )}
                    {exploreError && (
                        <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "8px" }}>{exploreError}</p>
                    )}

                    {/* Deep Analysis results */}
                    {analysis && (
                        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                            <div className="flex items-center gap-2 mb-5">
                                <div style={{ width: "3px", height: "16px", background: "var(--accent)" }} />
                                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--accent)", fontWeight: 600 }}>
                                    Deep Analysis
                                </span>
                            </div>
                            <div className="pl-4" style={{ borderLeft: "2px solid var(--border-subtle)", fontFamily: "var(--font-body)", fontSize: "0.92rem", lineHeight: 1.85, color: "var(--text-secondary)" }}>
                                {analysis.split("\n").filter(p => p.trim()).map((para, i) => {
                                    if (para.startsWith("**") && para.endsWith("**")) {
                                        return <h3 key={i} style={{ fontFamily: "var(--font-headline)", fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)", margin: i === 0 ? "0 0 8px 0" : "20px 0 8px 0", letterSpacing: "0.02em" }}>{para.replace(/\*\*/g, "")}</h3>;
                                    }
                                    if (para.startsWith("*") && para.endsWith("*")) {
                                        return <p key={i} style={{ fontStyle: "italic", color: "var(--text-dim)", fontSize: "0.8rem", margin: "16px 0 0 0" }}>{para.replace(/\*/g, "")}</p>;
                                    }
                                    return <p key={i} className="mb-3">{para}</p>;
                                })}
                            </div>
                        </motion.div>
                    )}
                </motion.div>

                {/* ─── Event Intelligence Results ─── */}
                {explore && explore.related_events.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="max-w-5xl mb-12"
                    >
                        <div className="separator mb-8" />

                        {/* Header with confidence badge */}
                        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
                            <div className="flex items-center gap-2">
                                <div style={{ width: "3px", height: "16px", background: "var(--accent)" }} />
                                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--accent)", fontWeight: 600 }}>
                                    Event Intelligence
                                </span>
                                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.6rem", color: "var(--text-dim)" }}>
                                    ({explore.related_events.length} events · {explore.total_candidates_scanned} scanned)
                                </span>
                            </div>
                            <span
                                className="px-3 py-1"
                                style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: "0.6rem",
                                    letterSpacing: "0.06em",
                                    textTransform: "uppercase",
                                    color: explore.confidence.level === "Strong" ? "#628DD3" : explore.confidence.level === "Moderate" ? "#FAB33B" : "var(--text-muted)",
                                    border: `1px solid ${explore.confidence.level === "Strong" ? "#628DD344" : explore.confidence.level === "Moderate" ? "#FAB33B44" : "var(--border-subtle)"}`,
                                    background: explore.confidence.level === "Strong" ? "#628DD30a" : explore.confidence.level === "Moderate" ? "#FAB33B0a" : "transparent",
                                }}
                            >
                                {explore.confidence.level} confidence
                            </span>
                        </div>

                        {/* Pattern type banner */}
                        {explore.signals_summary.dominant_pattern && (
                            <div
                                className="mb-6 p-4"
                                style={{
                                    background: "var(--accent-dim)",
                                    border: "1px solid var(--border-accent, #e85d5d22)",
                                }}
                            >
                                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.6rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-dim)", marginBottom: "4px" }}>
                                    DETECTED PATTERN
                                </div>
                                <div style={{ fontFamily: "var(--font-headline)", fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>
                                    {explore.signals_summary.dominant_pattern}
                                </div>
                                {explore.signals_summary.domains_covered.length > 0 && (
                                    <div className="flex gap-2 mt-2 flex-wrap">
                                        {explore.signals_summary.domains_covered.map((d) => (
                                            <span key={d} className="px-2 py-0.5" style={{ fontFamily: "var(--font-mono)", fontSize: "0.55rem", color: "var(--text-muted)", border: "1px solid var(--border-subtle)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                                                {d}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Related events grid */}
                        <div className="space-y-3 mb-8">
                            {explore.related_events.map((event, i) => (
                                <motion.div
                                    key={event.id}
                                    initial={{ opacity: 0, x: -8 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: i * 0.05 }}
                                >
                                    <Link
                                        href={`/article/${event.id}`}
                                        className="no-underline block"
                                        style={{ textDecoration: "none" }}
                                    >
                                        <div
                                            className="p-4 transition-all duration-200"
                                            style={{
                                                border: "1px solid var(--border-subtle)",
                                                background: "transparent",
                                            }}
                                            onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-surface)"; }}
                                            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                                        >
                                            <div className="flex items-start justify-between gap-3">
                                                <div style={{ flex: 1, minWidth: 0 }}>
                                                    {/* Meta row */}
                                                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                                                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.58rem", color: "var(--text-dim)" }}>
                                                            {event.source}
                                                        </span>
                                                        <span
                                                            className="px-2 py-0.5"
                                                            style={{
                                                                fontFamily: "var(--font-mono)",
                                                                fontSize: "0.5rem",
                                                                letterSpacing: "0.06em",
                                                                textTransform: "uppercase",
                                                                color: event.connection_type === "Cross-Domain" ? "var(--accent)" :
                                                                    event.connection_type === "Same Story" ? "#628DD3" :
                                                                        event.connection_type === "Shared Actors" ? "var(--accent)" : "var(--text-muted)",
                                                                border: `1px solid currentColor`,
                                                                opacity: 0.8,
                                                            }}
                                                        >
                                                            {event.connection_type}
                                                        </span>
                                                        {event.domain_transition && (
                                                            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", color: "var(--accent)", opacity: 0.7 }}>
                                                                {event.domain_transition}
                                                            </span>
                                                        )}
                                                    </div>
                                                    {/* Title */}
                                                    <h4 style={{ fontFamily: "var(--font-headline)", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-primary)", margin: "0 0 4px 0", lineHeight: 1.3 }}>
                                                        {event.title}
                                                    </h4>
                                                    {/* Shared entities */}
                                                    {event.shared_entities.length > 0 && (
                                                        <div className="flex items-center gap-1 flex-wrap mt-1">
                                                            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", color: "var(--text-dim)" }}>Shared:</span>
                                                            {event.shared_entities.slice(0, 3).map((ent) => (
                                                                <span key={ent} style={{ fontFamily: "var(--font-mono)", fontSize: "0.52rem", color: "var(--text-muted)", background: "var(--bg-surface)", padding: "1px 6px", border: "1px solid var(--border-subtle)" }}>
                                                                    {ent}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                                {/* Score indicator */}
                                                <div className="flex flex-col items-end gap-1" style={{ flexShrink: 0 }}>
                                                    <span style={{
                                                        fontFamily: "var(--font-mono)",
                                                        fontSize: "0.7rem",
                                                        fontWeight: 600,
                                                        color: event.relevance_score > 0.5 ? "var(--accent)" : event.relevance_score > 0.35 ? "var(--text-primary)" : "var(--text-muted)",
                                                    }}>
                                                        {(event.relevance_score * 100).toFixed(0)}%
                                                    </span>
                                                    {event.image_url && (
                                                        <img
                                                            src={event.image_url}
                                                            alt=""
                                                            style={{ width: "48px", height: "36px", objectFit: "cover", border: "1px solid var(--border-subtle)", opacity: 0.8 }}
                                                            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                                                        />
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </Link>
                                </motion.div>
                            ))}
                        </div>

                        {/* Narrative */}
                        <div className="mb-8">
                            <div className="flex items-center gap-2 mb-5">
                                <div style={{ width: "3px", height: "16px", background: "var(--text-primary)" }} />
                                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-primary)", fontWeight: 600 }}>
                                    Analysis
                                </span>
                            </div>
                            <div
                                className="pl-4"
                                style={{
                                    borderLeft: "2px solid var(--border-subtle)",
                                    fontFamily: "var(--font-body)",
                                    fontSize: "0.92rem",
                                    lineHeight: 1.85,
                                    color: "var(--text-secondary)",
                                }}
                            >
                                {explore.narrative.split("\n").filter(p => p.trim()).map((para, i) => {
                                    // Bold section headers
                                    if (para.startsWith("**") && para.includes("**")) {
                                        const headerMatch = para.match(/^\*\*(.+?)\*\*(.*)/);
                                        if (headerMatch) {
                                            return (
                                                <div key={i}>
                                                    <h3 style={{ fontFamily: "var(--font-headline)", fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)", margin: i === 0 ? "0 0 8px 0" : "20px 0 8px 0", letterSpacing: "0.02em" }}>
                                                        {headerMatch[1]}
                                                    </h3>
                                                    {headerMatch[2] && <p className="mb-3">{headerMatch[2]}</p>}
                                                </div>
                                            );
                                        }
                                    }
                                    // Bullet points
                                    if (para.startsWith("• ") || para.startsWith("- ")) {
                                        return <p key={i} className="mb-2" style={{ paddingLeft: "1rem" }}>{para}</p>;
                                    }
                                    // Italic lines
                                    if (para.startsWith("*") && para.endsWith("*")) {
                                        return <p key={i} style={{ fontStyle: "italic", color: "var(--text-dim)", fontSize: "0.8rem", margin: "16px 0 0 0" }}>{para.replace(/\*/g, "")}</p>;
                                    }
                                    return <p key={i} className="mb-3">{para}</p>;
                                })}
                            </div>
                        </div>

                        {/* Confidence details */}
                        <div
                            className="p-4"
                            style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)" }}
                        >
                            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.58rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-dim)", marginBottom: "6px" }}>
                                Confidence Assessment
                            </div>
                            <p style={{ fontFamily: "var(--font-body)", fontSize: "0.82rem", color: "var(--text-muted)", margin: 0, lineHeight: 1.6 }}>
                                {explore.confidence.description}
                            </p>
                        </div>
                    </motion.div>
                )}




                {/* Source link */}
                {article.url && (
                    <div className="max-w-5xl">
                        <div className="separator mb-4" />
                        <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "0.7rem",
                                color: "var(--text-muted)",
                                textDecoration: "none",
                            }}
                        >
                            Read original source →
                        </a>
                    </div>
                )}

                {/* ── Analytics Section (user-triggered) ─── */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="max-w-5xl mt-10"
                >
                    <div className="separator mb-4" />
                    <p style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.6rem",
                        letterSpacing: "0.12em",
                        textTransform: "uppercase",
                        color: "var(--text-dim)",
                        marginBottom: "12px",
                    }}>
                        Advanced Analytics
                    </p>
                    <div className="flex flex-wrap gap-3 mb-4">
                        <TimelinePanel articleId={resolvedParams.id} />
                        <BiasAnalysisPanel articleId={resolvedParams.id} />
                    </div>
                </motion.div>
            </div>
        </ClientShell>
    );
}
