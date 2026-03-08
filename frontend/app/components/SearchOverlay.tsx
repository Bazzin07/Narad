"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { ArticleSummary } from "../lib/api";

interface SearchOverlayProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function SearchOverlay({ isOpen, onClose }: SearchOverlayProps) {
    const router = useRouter();
    const inputRef = useRef<HTMLInputElement>(null);
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<ArticleSummary[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setTimeout(() => inputRef.current?.focus(), 100);
            setQuery("");
            setResults([]);
        }
    }, [isOpen]);

    useEffect(() => {
        if (!query.trim()) {
            setResults([]);
            return;
        }
        const timeout = setTimeout(async () => {
            setLoading(true);
            try {
                const res = await fetch(
                    `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/news?limit=50`
                );
                const articles: ArticleSummary[] = await res.json();
                const q = query.toLowerCase();
                const filtered = articles.filter(
                    (a) =>
                        a.title.toLowerCase().includes(q) ||
                        a.source.toLowerCase().includes(q) ||
                        (a.topic && a.topic.toLowerCase().includes(q))
                );
                setResults(filtered.slice(0, 8));
            } catch {
                setResults([]);
            }
            setLoading(false);
        }, 200);
        return () => clearTimeout(timeout);
    }, [query]);

    const handleSelect = (article: ArticleSummary) => {
        onClose();
        router.push(`/article/${article.id}`);
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]"
                    style={{ backdropFilter: "blur(8px)", background: "rgba(255,255,255,0.85)" }}
                    onClick={onClose}
                >
                    <motion.div
                        initial={{ opacity: 0, y: -20, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2 }}
                        className="w-full max-w-2xl"
                        style={{ padding: "0 var(--page-gutter)" }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Input */}
                        <div
                            className="flex items-center gap-3 px-5 py-4"
                            style={{
                                background: "var(--bg-deep)",
                                border: "1px solid var(--border-visible)",
                                borderBottom: results.length ? "none" : undefined,
                                boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
                            }}
                        >
                            <svg
                                width="18"
                                height="18"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="var(--text-muted)"
                                strokeWidth="2"
                            >
                                <circle cx="11" cy="11" r="8" />
                                <path d="m21 21-4.3-4.3" />
                            </svg>
                            <input
                                ref={inputRef}
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Search articles, topics, sources..."
                                className="flex-1 bg-transparent border-none outline-none"
                                style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: "0.9rem",
                                    color: "var(--text-primary)",
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === "Escape") onClose();
                                    if (e.key === "Enter" && results.length > 0) {
                                        handleSelect(results[0]);
                                    }
                                }}
                            />
                            {loading && (
                                <div
                                    className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin"
                                    style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
                                />
                            )}
                            <kbd
                                style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: "0.6rem",
                                    color: "var(--text-muted)",
                                    background: "var(--bg-surface)",
                                    padding: "2px 6px",
                                }}
                            >
                                ESC
                            </kbd>
                        </div>

                        {/* Results */}
                        {results.length > 0 && (
                            <div
                                style={{
                                    background: "var(--bg-deep)",
                                    border: "1px solid var(--border-visible)",
                                    borderTop: "1px solid var(--border-subtle)",
                                    maxHeight: "400px",
                                    overflowY: "auto",
                                    boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
                                }}
                            >
                                {results.map((article, i) => (
                                    <motion.button
                                        key={article.id}
                                        initial={{ opacity: 0, x: -8 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.03 }}
                                        onClick={() => handleSelect(article)}
                                        className="w-full text-left px-5 py-3 flex items-start gap-4 transition-colors"
                                        style={{
                                            background: "transparent",
                                            border: "none",
                                            borderBottom: "1px solid var(--border-subtle)",
                                            cursor: "pointer",
                                        }}
                                        onMouseEnter={(e) =>
                                            (e.currentTarget.style.background = "var(--bg-hover)")
                                        }
                                        onMouseLeave={(e) =>
                                            (e.currentTarget.style.background = "transparent")
                                        }
                                    >
                                        <div className="flex-1 min-w-0">
                                            <p
                                                className="m-0 truncate"
                                                style={{
                                                    fontFamily: "var(--font-headline)",
                                                    fontSize: "0.85rem",
                                                    color: "var(--text-primary)",
                                                }}
                                            >
                                                {article.title}
                                            </p>
                                            <p
                                                className="m-0 mt-1"
                                                style={{
                                                    fontFamily: "var(--font-mono)",
                                                    fontSize: "0.65rem",
                                                    color: "var(--text-muted)",
                                                }}
                                            >
                                                {article.source}
                                                {article.topic && article.topic !== "general" && (
                                                    <span style={{ color: "var(--accent)", marginLeft: "8px" }}>
                                                        {article.topic}
                                                    </span>
                                                )}
                                            </p>
                                        </div>
                                        <span
                                            style={{
                                                fontFamily: "var(--font-mono)",
                                                fontSize: "0.6rem",
                                                color: "var(--text-dim)",
                                                whiteSpace: "nowrap",
                                            }}
                                        >
                                            {article.language.toUpperCase()}
                                        </span>
                                    </motion.button>
                                ))}
                            </div>
                        )}
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
