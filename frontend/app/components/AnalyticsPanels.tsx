"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    getTimeline, getBiasAnalysis,
    type TimelineResponse, type BiasAnalysisResponse,
} from "../lib/api";

// ── Shared Button Style ──────────────────────────────────────────────────────

const btnStyle = (color: string, active: boolean) => ({
    fontFamily: "var(--font-mono)",
    fontSize: "0.65rem",
    letterSpacing: "0.08em",
    textTransform: "uppercase" as const,
    color: active ? "#fff" : color,
    background: active ? color : "transparent",
    border: `1px solid ${color}`,
    padding: "8px 18px",
    display: "inline-flex" as const,
    alignItems: "center" as const,
    gap: "8px",
    cursor: "pointer" as const,
    transition: "all 0.2s",
    opacity: 1,
});

// ── Sentiment Dot ────────────────────────────────────────────────────────────

function SentimentDot({ score }: { score: number | null }) {
    if (score === null || score === undefined) return null;
    const color = score > 0.3 ? "#628DD3" : score < -0.3 ? "#E85D5D" : "#FAB33B";
    const label = score > 0.3 ? "Positive" : score < -0.3 ? "Negative" : "Neutral";
    return (
        <span title={`Sentiment: ${label} (${score.toFixed(2)})`} style={{
            display: "inline-block", width: "8px", height: "8px", borderRadius: "50%",
            background: color, boxShadow: `0 0 6px ${color}66`,
        }} />
    );
}

// ── Event Timeline Component ─────────────────────────────────────────────────

export function TimelinePanel({ articleId }: { articleId: string }) {
    const [data, setData] = useState<TimelineResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const load = async () => {
        setLoading(true);
        setError("");
        try {
            const result = await getTimeline(articleId);
            setData(result);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Failed to load timeline");
        }
        setLoading(false);
    };

    return (
        <div className={data ? "w-full max-w-full overflow-hidden" : ""}>
            {!data && !loading && (
                <button
                    onClick={load}
                    style={btnStyle("var(--accent)", false)}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "var(--accent)"; e.currentTarget.style.color = "#fff"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--accent)"; }}
                >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2v20M2 12h20M2 7h6M16 7h6M5 17h14" /></svg>
                    Event Timeline
                </button>
            )}

            {loading && (
                <div className="p-4" style={{ border: "1px solid var(--border-accent)", background: "var(--accent-dim)" }}>
                    <div className="flex items-center gap-3">
                        <div className="live-dot" style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)" }} />
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--accent)" }}>
                            Building event timeline...
                        </span>
                    </div>
                </div>
            )}

            {error && <p style={{ color: "#ef4444", fontSize: "0.8rem" }}>{error}</p>}

            <AnimatePresence>
                {data && (
                    <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="mt-4"
                    >
                        <div className="flex items-center gap-2 mb-3">
                            <h3 style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "0.7rem",
                                letterSpacing: "0.08em",
                                textTransform: "uppercase",
                                color: "var(--accent)",
                                margin: 0,
                            }}>
                                ⏱ Event Timeline ({data.total_events} events)
                            </h3>
                        </div>

                        {/* Horizontal scrollable timeline */}
                        <div style={{
                            overflowX: "auto",
                            padding: "16px 0",
                            position: "relative",
                        }}>
                            <div style={{
                                display: "flex",
                                gap: "0",
                                minWidth: "fit-content",
                                position: "relative",
                            }}>
                                {/* Connecting line */}
                                <div style={{
                                    position: "absolute",
                                    top: "24px",
                                    left: "0",
                                    right: "0",
                                    height: "2px",
                                    background: "linear-gradient(90deg, var(--accent-dim), var(--accent), var(--accent-dim))",
                                    zIndex: 0,
                                }} />

                                {data.timeline.map((event, idx) => (
                                    <motion.div
                                        key={event.id}
                                        initial={{ opacity: 0, y: 12 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: idx * 0.05 }}
                                        style={{
                                            minWidth: "200px",
                                            maxWidth: "220px",
                                            padding: "0 12px",
                                            position: "relative",
                                            zIndex: 1,
                                        }}
                                    >
                                        {/* Timeline dot */}
                                        <div style={{
                                            width: event.is_seed ? "16px" : "10px",
                                            height: event.is_seed ? "16px" : "10px",
                                            borderRadius: "50%",
                                            background: event.is_seed ? "var(--accent)" : "var(--bg-surface)",
                                            border: `2px solid ${event.is_seed ? "var(--accent)" : "var(--border-accent)"}`,
                                            margin: `${event.is_seed ? "16px" : "19px"} auto 12px`,
                                            boxShadow: event.is_seed ? "0 0 12px var(--accent-glow)" : "none",
                                        }} />

                                        {/* Date */}
                                        <p style={{
                                            fontFamily: "var(--font-mono)",
                                            fontSize: "0.55rem",
                                            color: "var(--text-muted)",
                                            textAlign: "center",
                                            margin: "0 0 6px",
                                        }}>
                                            {new Date(event.published_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                                        </p>

                                        {/* Card */}
                                        <div style={{
                                            padding: "10px",
                                            background: event.is_seed ? "var(--accent-dim)" : "var(--bg-surface)",
                                            border: `1px solid ${event.is_seed ? "var(--accent)" : "var(--border-primary)"}`,
                                            borderRadius: "6px",
                                        }}>
                                            <div className="flex items-center gap-1 mb-1">
                                                <SentimentDot score={event.sentiment} />
                                                <span style={{
                                                    fontFamily: "var(--font-mono)",
                                                    fontSize: "0.5rem",
                                                    color: "var(--text-dim)",
                                                    letterSpacing: "0.05em",
                                                }}>
                                                    {event.source}
                                                </span>
                                            </div>
                                            <p style={{
                                                fontSize: "0.72rem",
                                                fontWeight: 500,
                                                lineHeight: 1.3,
                                                margin: "0 0 4px",
                                                display: "-webkit-box",
                                                WebkitLineClamp: 3,
                                                WebkitBoxOrient: "vertical",
                                                overflow: "hidden",
                                            }}>{event.title}</p>
                                            {event.key_entities.length > 0 && (
                                                <div className="flex flex-wrap gap-1">
                                                    {event.key_entities.slice(0, 3).map(e => (
                                                        <span key={e} style={{
                                                            fontFamily: "var(--font-mono)",
                                                            fontSize: "0.45rem",
                                                            padding: "1px 4px",
                                                            background: "var(--accent-dim)",
                                                            color: "var(--accent)",
                                                            border: "1px solid var(--border-accent)",
                                                        }}>{e}</span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}



// ── Source Bias Analysis Component ────────────────────────────────────────────

export function BiasAnalysisPanel({ articleId }: { articleId: string }) {
    const [data, setData] = useState<BiasAnalysisResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const load = async () => {
        setLoading(true);
        setError("");
        try {
            const result = await getBiasAnalysis(articleId);
            setData(result);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Failed to analyze bias");
        }
        setLoading(false);
    };

    const sentColor = (label: string) =>
        label === "Positive" ? "#628DD3" : label === "Negative" ? "#E85D5D" : "#FAB33B";

    return (
        <div>
            {!data && !loading && (
                <button
                    onClick={load}
                    style={btnStyle("var(--accent)", false)}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "var(--accent)"; e.currentTarget.style.color = "#fff"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--accent)"; }}
                >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" /><line x1="4" y1="22" x2="4" y2="15" />
                    </svg>
                    Compare Coverage
                </button>
            )}

            {loading && (
                <div className="p-4" style={{ border: "1px solid var(--border-accent)", background: "var(--accent-dim)" }}>
                    <div className="flex items-center gap-3">
                        <div className="live-dot" style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)" }} />
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--accent)" }}>
                            Analyzing source coverage bias...
                        </span>
                    </div>
                </div>
            )}

            {error && <p style={{ color: "#ef4444", fontSize: "0.8rem" }}>{error}</p>}

            <AnimatePresence>
                {data && data.comparisons.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="mt-4"
                    >
                        <h3 style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.7rem",
                            letterSpacing: "0.08em",
                            textTransform: "uppercase",
                            color: "var(--accent)",
                            margin: "0 0 12px",
                        }}>
                            📊 Source Coverage Comparison ({data.total_sources} sources)
                        </h3>

                        {/* Source cards */}
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "10px" }}>
                            {data.comparisons.map((comp, idx) => (
                                <motion.div
                                    key={comp.id}
                                    initial={{ opacity: 0, x: -8 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: idx * 0.08 }}
                                    style={{
                                        padding: "12px",
                                        background: "var(--bg-surface)",
                                        border: "1px solid var(--border-primary)",
                                        borderRadius: "8px",
                                        borderLeft: `3px solid ${sentColor(comp.sentiment_label)}`,
                                    }}
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <span style={{
                                            fontFamily: "var(--font-mono)",
                                            fontSize: "0.6rem",
                                            fontWeight: 600,
                                            color: "var(--text-secondary)",
                                        }}>{comp.source}</span>
                                        <span style={{
                                            fontFamily: "var(--font-mono)",
                                            fontSize: "0.5rem",
                                            padding: "2px 6px",
                                            borderRadius: "3px",
                                            background: `${sentColor(comp.sentiment_label)}22`,
                                            color: sentColor(comp.sentiment_label),
                                            border: `1px solid ${sentColor(comp.sentiment_label)}44`,
                                        }}>
                                            {comp.sentiment_label}
                                        </span>
                                    </div>
                                    <p style={{
                                        fontSize: "0.72rem",
                                        lineHeight: 1.35,
                                        margin: "0 0 6px",
                                        display: "-webkit-box",
                                        WebkitLineClamp: 2,
                                        WebkitBoxOrient: "vertical",
                                        overflow: "hidden",
                                    }}>{comp.title}</p>
                                    <div className="flex items-center gap-2">
                                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.45rem", color: "var(--text-dim)" }}>
                                            {comp.language.toUpperCase()} · {(comp.similarity * 100).toFixed(0)}% match
                                        </span>
                                    </div>
                                </motion.div>
                            ))}
                        </div>

                        {/* Narrative */}
                        {data.narrative && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 0.3 }}
                                className="mt-4 p-4"
                                style={{
                                    background: "var(--accent-dim)",
                                    border: "1px solid var(--border-accent)",
                                    borderRadius: "8px",
                                }}
                            >
                                <p style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: "0.55rem",
                                    color: "var(--accent)",
                                    marginBottom: "8px",
                                    letterSpacing: "0.08em",
                                    textTransform: "uppercase",
                                }}>Analysis</p>
                                <div style={{
                                    fontSize: "0.8rem",
                                    lineHeight: 1.6,
                                    color: "var(--text-secondary)",
                                    whiteSpace: "pre-wrap",
                                }}>
                                    {data.narrative}
                                </div>
                            </motion.div>
                        )}
                    </motion.div>
                )}
                {data && data.comparisons.length === 0 && (
                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "8px" }}
                    >
                        No alternative source coverage found for this event.
                    </motion.p>
                )}
            </AnimatePresence>
        </div>
    );
}
