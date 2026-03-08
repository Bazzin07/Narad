"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ClientShell from "../components/ClientShell";
import ArticleCard from "../components/ArticleCard";
import { getArticles, type ArticleSummary } from "../lib/api";

const ARTICLES_PER_PAGE = 20;
const POLL_INTERVAL_MS = 60000; // 60 seconds (slower for global)

export default function GlobalNewsPage() {
    const [language, setLanguage] = useState("en");
    const [articles, setArticles] = useState<ArticleSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [fetchError, setFetchError] = useState<string | null>(null);
    const [page, setPage] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [newArticleIds, setNewArticleIds] = useState<Set<string>>(new Set());
    const knownIds = useRef(new Set<string>());

    const fetchArticles = useCallback(async () => {
        setLoading(true);
        setFetchError(null);
        try {
            const arts = await getArticles({
                limit: ARTICLES_PER_PAGE,
                language: language === "all" ? undefined : language,
                region: "global",
            });
            setArticles(arts);
            setPage(0);
            setHasMore(arts.length === ARTICLES_PER_PAGE);
            knownIds.current = new Set(arts.map((a) => a.id));
            setNewArticleIds(new Set());
        } catch (err) {
            console.error("Failed to load:", err);
            setFetchError(
                err instanceof Error && err.message.includes("abort")
                    ? "Request timed out. The server may be busy."
                    : "Failed to load articles. Please check if the backend is running."
            );
        }
        setLoading(false);
    }, [language]);

    useEffect(() => {
        fetchArticles();
    }, [fetchArticles]);

    // Polling
    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                const latest = await getArticles({
                    limit: 10,
                    language: language === "all" ? undefined : language,
                    region: "global",
                });
                const newOnes = latest.filter((a) => !knownIds.current.has(a.id));
                if (newOnes.length > 0) {
                    setArticles((prev) => {
                        const combined = [...newOnes, ...prev];
                        const seen = new Set<string>();
                        return combined.filter((a) => {
                            if (seen.has(a.id)) return false;
                            seen.add(a.id);
                            return true;
                        });
                    });
                    const newIds = new Set(newOnes.map((a) => a.id));
                    setNewArticleIds(newIds);
                    newOnes.forEach((a) => knownIds.current.add(a.id));
                    setTimeout(() => setNewArticleIds(new Set()), 30000);
                }
            } catch (err) {
                console.error("Polling failed:", err);
            }
        }, POLL_INTERVAL_MS);
        return () => clearInterval(interval);
    }, [language]);

    // Pagination
    const loadMore = useCallback(async () => {
        if (loadingMore || !hasMore) return;
        setLoadingMore(true);
        try {
            const nextPage = page + 1;
            const more = await getArticles({
                limit: ARTICLES_PER_PAGE,
                offset: nextPage * ARTICLES_PER_PAGE,
                language: language === "all" ? undefined : language,
                region: "global",
            });
            if (more.length > 0) {
                setArticles((prev) => {
                    const combined = [...prev, ...more];
                    const seen = new Set<string>();
                    return combined.filter((a) => {
                        if (seen.has(a.id)) return false;
                        seen.add(a.id);
                        return true;
                    });
                });
                more.forEach((a) => knownIds.current.add(a.id));
                setPage(nextPage);
                setHasMore(more.length === ARTICLES_PER_PAGE);
            } else {
                setHasMore(false);
            }
        } catch (err) {
            console.error("Load more failed:", err);
        }
        setLoadingMore(false);
    }, [page, loadingMore, hasMore, language]);

    return (
        <ClientShell language={language} onLanguageChange={setLanguage}>
            <div style={{ padding: "2rem var(--page-gutter) 4rem" }}>
                {/* Hero */}
                <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="mb-8"
                >
                    <div className="flex items-center gap-3 mb-3">
                        <div style={{
                            width: "8px", height: "8px", borderRadius: "50%",
                            background: "var(--accent)",
                        }} />
                        <span style={{
                            fontFamily: "var(--font-mono)", fontSize: "0.7rem",
                            letterSpacing: "0.12em", textTransform: "uppercase",
                            color: "var(--accent)",
                        }}>
                            Global
                        </span>
                    </div>
                    <h1 style={{
                        fontFamily: "var(--font-headline)",
                        fontSize: "clamp(2rem, 4.5vw, 3.5rem)",
                        fontWeight: 600, lineHeight: 1.1,
                        color: "var(--text-primary)", margin: 0,
                    }}>
                        World News
                    </h1>
                    <p className="mt-3 max-w-xl" style={{
                        fontFamily: "var(--font-body)", fontSize: "0.9rem",
                        color: "var(--text-secondary)", lineHeight: 1.6,
                    }}>
                        International coverage from BBC, CNN, Reuters, NYT, and other global outlets.
                    </p>
                </motion.div>

                <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
                    {loading ? (
                        <div className="space-y-4">
                            {[...Array(6)].map((_, i) => (
                                <div key={i} className="py-5" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                                    <div className="flex gap-4">
                                        <div style={{ flex: 1 }}>
                                            <div className="h-3 mb-2 animate-pulse" style={{ width: "30%", background: "var(--bg-surface)" }} />
                                            <div className="h-5 mb-1 animate-pulse" style={{ width: "80%", background: "var(--bg-surface)" }} />
                                            <div className="h-5 animate-pulse" style={{ width: "60%", background: "var(--bg-surface)" }} />
                                        </div>
                                        <div className="animate-pulse" style={{
                                            width: "140px", height: "90px",
                                            background: "var(--bg-surface)", borderRadius: "4px", flexShrink: 0,
                                        }} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : fetchError ? (
                        <div className="py-16 text-center">
                            <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
                                {fetchError}
                            </p>
                            <button
                                onClick={fetchArticles}
                                className="px-6 py-2 cursor-pointer transition-all duration-200"
                                style={{
                                    fontFamily: "var(--font-mono)", fontSize: "0.7rem",
                                    letterSpacing: "0.08em", textTransform: "uppercase",
                                    color: "var(--accent)", background: "transparent",
                                    border: "1px solid var(--accent)", borderRadius: "4px",
                                }}
                            >
                                Retry
                            </button>
                        </div>
                    ) : articles.length === 0 ? (
                        <div className="py-16 text-center">
                            <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                                No global stories found
                            </p>
                        </div>
                    ) : (
                        <>
                            <AnimatePresence mode="popLayout">
                                {articles.map((article, i) => (
                                    <ArticleCard
                                        key={article.id}
                                        article={article}
                                        index={i}
                                        isNew={newArticleIds.has(article.id)}
                                    />
                                ))}
                            </AnimatePresence>

                            {hasMore && (
                                <div className="py-8 text-center">
                                    <button
                                        onClick={loadMore}
                                        disabled={loadingMore}
                                        className="px-6 py-2 cursor-pointer transition-all duration-200"
                                        style={{
                                            fontFamily: "var(--font-mono)", fontSize: "0.7rem",
                                            letterSpacing: "0.08em", textTransform: "uppercase",
                                            color: loadingMore ? "var(--text-dim)" : "var(--text-secondary)",
                                            background: "transparent", border: "1px solid var(--border-subtle)",
                                        }}
                                    >
                                        {loadingMore ? "Loading..." : "Load More"}
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </ClientShell>
    );
}
