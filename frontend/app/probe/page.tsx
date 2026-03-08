"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import ClientShell from "../components/ClientShell";
import { probe, type ProbeMatch } from "../lib/api";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ProbePage() {
    const [language, setLanguage] = useState("all");
    const [text, setText] = useState("");
    const [source, setSource] = useState("");
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<ProbeMatch[] | null>(null);
    const [overview, setOverview] = useState<string>("");
    const [error, setError] = useState<string>("");

    const handleAnalyze = async () => {
        if (!text.trim()) return;
        setLoading(true);
        setError("");
        setResults(null);
        try {
            const data = await probe(text, source || "user-input", false);
            setResults(data.matches);
            setOverview(data.overview_map || data.analysis_summary || "");
        } catch (err) {
            setError("Analysis failed. Make sure the backend is running.");
            console.error(err);
        }
        setLoading(false);
    };

    const getScore = (match: ProbeMatch) => match.relation_score.total_score;

    const getStrengthColor = (score: number) => {
        if (score >= 0.5) return "var(--accent)";
        if (score >= 0.4) return "#FAB33B";
        return "var(--text-muted)";
    };

    const getStrengthLabel = (score: number) => {
        if (score >= 0.5) return "STRONG";
        if (score >= 0.4) return "RELATED";
        return "WEAK";
    };

    return (
        <ClientShell language={language} onLanguageChange={setLanguage}>
            <div style={{ padding: "2rem var(--page-gutter) 4rem", maxWidth: "900px", margin: "0 auto" }}>
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <span
                        className="block mb-2"
                        style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.7rem",
                            letterSpacing: "0.12em",
                            textTransform: "uppercase",
                            color: "var(--accent)",
                        }}
                    >
                        Feature: News Probe
                    </span>
                    <h1
                        style={{
                            fontFamily: "var(--font-headline)",
                            fontSize: "clamp(2rem, 4vw, 3rem)",
                            fontWeight: 600,
                            margin: 0,
                        }}
                    >
                        Probe Intelligence
                    </h1>
                    <p
                        className="mt-2"
                        style={{
                            fontFamily: "var(--font-body)",
                            fontSize: "0.85rem",
                            color: "var(--text-secondary)",
                        }}
                    >
                        Paste any news text. Narad will find hidden connections across the entire corpus.
                    </p>
                </motion.div>

                {/* Terminal-style input */}
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 }}
                    className="mb-8"
                >
                    <div
                        style={{
                            background: "var(--bg-elevated)",
                            border: "1px solid var(--border-subtle)",
                        }}
                    >
                        {/* Terminal header */}
                        <div
                            className="flex items-center gap-2 px-4 py-2"
                            style={{ borderBottom: "1px solid var(--border-subtle)" }}
                        >
                            <div className="flex gap-1.5">
                                <div className="w-2.5 h-2.5 rounded-full" style={{ background: "#CA8076" }} />
                                <div className="w-2.5 h-2.5 rounded-full" style={{ background: "#FAB33B" }} />
                                <div className="w-2.5 h-2.5 rounded-full" style={{ background: "#628DD3" }} />
                            </div>
                            <span
                                style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: "0.6rem",
                                    color: "var(--text-dim)",
                                    marginLeft: "8px",
                                }}
                            >
                                narad://probe/input
                            </span>
                        </div>

                        {/* Text area */}
                        <div className="p-4">
                            <div className="flex items-start gap-2">
                                <span
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: "0.8rem",
                                        color: "var(--accent)",
                                        lineHeight: "1.6",
                                        userSelect: "none",
                                    }}
                                >
                                    $
                                </span>
                                <textarea
                                    value={text}
                                    onChange={(e) => setText(e.target.value)}
                                    placeholder="Paste news text, headlines, or intelligence here..."
                                    rows={6}
                                    className="flex-1 bg-transparent border-none outline-none resize-none"
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: "0.8rem",
                                        color: "var(--text-primary)",
                                        lineHeight: 1.6,
                                    }}
                                />
                            </div>

                            <div className="flex items-center gap-2 mt-3 pt-3" style={{ borderTop: "1px solid var(--border-subtle)" }}>
                                <span
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: "0.65rem",
                                        color: "var(--text-dim)",
                                    }}
                                >
                                    SOURCE:
                                </span>
                                <input
                                    value={source}
                                    onChange={(e) => setSource(e.target.value)}
                                    placeholder="reuters, bbc, twitter..."
                                    className="flex-1 bg-transparent border-none outline-none"
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: "0.7rem",
                                        color: "var(--text-secondary)",
                                    }}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Analyze button */}
                    <div className="mt-4 flex items-center gap-4">
                        <button
                            onClick={handleAnalyze}
                            disabled={loading || !text.trim()}
                            className="px-6 py-2.5 transition-all duration-300"
                            style={{
                                background: text.trim() ? "var(--accent)" : "var(--bg-surface)",
                                color: text.trim() ? "#FFFFFF" : "var(--text-muted)",
                                border: "none",
                                fontFamily: "var(--font-mono)",
                                fontSize: "0.75rem",
                                fontWeight: 600,
                                letterSpacing: "0.08em",
                                textTransform: "uppercase",
                                cursor: text.trim() ? "pointer" : "not-allowed",
                                boxShadow: text.trim() ? "0 0 20px var(--accent-glow)" : "none",
                            }}
                        >
                            {loading ? "Analyzing..." : "Analyze"}
                        </button>

                        {loading && (
                            <div className="flex items-center gap-2">
                                <div
                                    className="w-3 h-3 border-2 border-t-transparent rounded-full animate-spin"
                                    style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
                                />
                                <span
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: "0.65rem",
                                        color: "var(--text-muted)",
                                    }}
                                >
                                    Scanning corpus...
                                </span>
                            </div>
                        )}
                    </div>
                </motion.div>

                {/* Error */}
                {error && (
                    <div
                        className="mb-6 p-4"
                        style={{
                            background: "var(--accent-dim)",
                            border: "1px solid var(--border-accent)",
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.75rem",
                            color: "var(--accent)",
                        }}
                    >
                        {error}
                    </div>
                )}

                {/* Results */}
                <AnimatePresence>
                    {results && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
                            {overview && (
                                <motion.div
                                    initial={{ opacity: 0, y: 12 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="mb-8 p-5"
                                    style={{
                                        background: "var(--bg-elevated)",
                                        border: "1px solid var(--border-subtle)",
                                        borderLeft: "2px solid var(--accent)",
                                    }}
                                >
                                    <span
                                        className="block mb-2"
                                        style={{
                                            fontFamily: "var(--font-mono)",
                                            fontSize: "0.6rem",
                                            letterSpacing: "0.1em",
                                            textTransform: "uppercase",
                                            color: "var(--text-dim)",
                                        }}
                                    >
                                        Analysis Overview
                                    </span>
                                    <div style={{
                                        fontFamily: "var(--font-body)",
                                        fontSize: "0.88rem",
                                        color: "var(--text-secondary)",
                                        lineHeight: 1.8,
                                    }}>
                                        <ReactMarkdown
                                            remarkPlugins={[remarkGfm]}
                                            components={{
                                                p: ({ node, ...props }) => <p style={{ marginBottom: "0.9em", marginTop: 0 }} {...props} />,
                                                strong: ({ node, ...props }) => <strong style={{ color: "var(--text-primary)", fontWeight: 600 }} {...props} />,
                                                em: ({ node, ...props }) => <em style={{ color: "var(--text-muted)", fontStyle: "italic" }} {...props} />,
                                                ul: ({ node, ...props }) => <ul style={{ marginBottom: "0.9em", paddingLeft: "1.4em", listStyleType: "disc" }} {...props} />,
                                                ol: ({ node, ...props }) => <ol style={{ marginBottom: "0.9em", paddingLeft: "1.4em", listStyleType: "decimal" }} {...props} />,
                                                li: ({ node, ...props }) => <li style={{ marginBottom: "0.3em" }} {...props} />,
                                                blockquote: ({ node, ...props }) => (
                                                    <blockquote
                                                        style={{
                                                            borderLeft: "3px solid var(--accent)",
                                                            paddingLeft: "1rem",
                                                            margin: "0.8em 0",
                                                            color: "var(--text-secondary)",
                                                            fontStyle: "normal",
                                                        }}
                                                        {...props}
                                                    />
                                                ),
                                                hr: () => <hr style={{ border: "none", borderTop: "1px solid var(--border-subtle)", margin: "1em 0" }} />,
                                                h1: ({ node, ...props }) => <h2 style={{ color: "var(--text-primary)", fontFamily: "var(--font-headline)", fontSize: "1.05rem", fontWeight: 600, marginBottom: "0.4em", marginTop: "1em" }} {...props} />,
                                                h2: ({ node, ...props }) => <h3 style={{ color: "var(--text-primary)", fontFamily: "var(--font-headline)", fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.4em", marginTop: "0.8em" }} {...props} />,
                                            }}
                                        >
                                            {overview}
                                        </ReactMarkdown>
                                    </div>
                                </motion.div>
                            )}

                            <div className="flex items-center gap-2 mb-4">
                                <span
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: "0.7rem",
                                        letterSpacing: "0.08em",
                                        textTransform: "uppercase",
                                        color: "var(--text-muted)",
                                    }}
                                >
                                    {results.length} Connections Found
                                </span>
                            </div>

                            <div className="space-y-3">
                                {results.map((match, i) => {
                                    const score = getScore(match);
                                    return (
                                        <motion.div
                                            key={match.article.id}
                                            initial={{ opacity: 0, x: -16 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: i * 0.08 }}
                                        >
                                            <Link
                                                href={`/article/${match.article.id}`}
                                                className="block no-underline"
                                                style={{ textDecoration: "none" }}
                                            >
                                                <div
                                                    className="p-5 transition-all duration-300"
                                                    style={{
                                                        background: "var(--bg-elevated)",
                                                        border: "1px solid var(--border-subtle)",
                                                    }}
                                                    onMouseEnter={(e) => {
                                                        e.currentTarget.style.borderColor = "var(--border-accent)";
                                                    }}
                                                    onMouseLeave={(e) => {
                                                        e.currentTarget.style.borderColor = "var(--border-subtle)";
                                                    }}
                                                >
                                                    {/* Score bar */}
                                                    <div className="flex items-center gap-3 mb-3">
                                                        <div
                                                            style={{ flex: 1, height: "2px", background: "var(--bg-surface)" }}
                                                        >
                                                            <motion.div
                                                                initial={{ width: 0 }}
                                                                animate={{ width: `${score * 100}%` }}
                                                                transition={{ delay: i * 0.08 + 0.3, duration: 0.6 }}
                                                                style={{ height: "2px", background: getStrengthColor(score) }}
                                                            />
                                                        </div>
                                                        <span
                                                            style={{
                                                                fontFamily: "var(--font-mono)",
                                                                fontSize: "0.65rem",
                                                                color: getStrengthColor(score),
                                                                minWidth: "60px",
                                                                textAlign: "right",
                                                            }}
                                                        >
                                                            {getStrengthLabel(score)} {(score * 100).toFixed(0)}%
                                                        </span>
                                                    </div>

                                                    <h3
                                                        className="m-0 mb-2"
                                                        style={{
                                                            fontFamily: "var(--font-headline)",
                                                            fontSize: "0.95rem",
                                                            fontWeight: 500,
                                                            color: "var(--text-primary)",
                                                            lineHeight: 1.35,
                                                        }}
                                                    >
                                                        {match.article.title}
                                                    </h3>

                                                    <div className="flex items-center gap-3">
                                                        <span
                                                            style={{
                                                                fontFamily: "var(--font-mono)",
                                                                fontSize: "0.6rem",
                                                                color: "var(--text-muted)",
                                                            }}
                                                        >
                                                            {match.article.source}
                                                        </span>
                                                        {match.shared_entities.length > 0 && (
                                                            <>
                                                                <span style={{ color: "var(--text-dim)" }}>·</span>
                                                                <span
                                                                    style={{
                                                                        fontFamily: "var(--font-mono)",
                                                                        fontSize: "0.6rem",
                                                                        color: "var(--accent)",
                                                                        opacity: 0.7,
                                                                    }}
                                                                >
                                                                    Shared: {match.shared_entities.slice(0, 3).join(", ")}
                                                                </span>
                                                            </>
                                                        )}
                                                    </div>
                                                </div>
                                            </Link>
                                        </motion.div>
                                    );
                                })}
                            </div>

                            {results.length === 0 && (
                                <div
                                    className="py-12 text-center"
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: "0.8rem",
                                        color: "var(--text-muted)",
                                    }}
                                >
                                    No connections found in the current corpus.
                                </div>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </ClientShell>
    );
}
