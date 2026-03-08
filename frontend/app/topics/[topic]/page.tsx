"use client";

import { useState, useEffect, use } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import ClientShell from "../../components/ClientShell";
import ArticleCard from "../../components/ArticleCard";
import { getTopicArticles, type ArticleSummary } from "../../lib/api";

export default function TopicPage({ params }: { params: Promise<{ topic: string }> }) {
    const resolvedParams = use(params);
    const [language, setLanguage] = useState("all");
    const [articles, setArticles] = useState<ArticleSummary[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getTopicArticles(resolvedParams.topic, 50)
            .then(setArticles)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [resolvedParams.topic]);

    return (
        <ClientShell language={language} onLanguageChange={setLanguage}>
            <div style={{ padding: "2rem var(--page-gutter) 4rem", maxWidth: "1200px", margin: "0 auto" }}>
                <Link
                    href="/topics"
                    className="no-underline inline-flex items-center gap-2 mb-6"
                    style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.7rem",
                        color: "var(--text-muted)",
                        textDecoration: "none",
                    }}
                >
                    ← TOPICS
                </Link>

                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
                    <h1
                        style={{
                            fontFamily: "var(--font-serif)",
                            fontSize: "clamp(2rem, 4vw, 3rem)",
                            fontWeight: 400,
                            textTransform: "capitalize",
                            margin: 0,
                        }}
                    >
                        {resolvedParams.topic}
                    </h1>
                    <p
                        className="mt-2"
                        style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.75rem",
                            color: "var(--text-muted)",
                        }}
                    >
                        {articles.length} events classified under this topic
                    </p>
                </motion.div>

                <div className="separator mb-6" />

                {loading ? (
                    <div className="space-y-4">
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="py-4 animate-pulse" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                                <div className="h-5 w-3/4 mb-2" style={{ background: "var(--bg-surface)" }} />
                                <div className="h-3 w-1/3" style={{ background: "var(--bg-surface)" }} />
                            </div>
                        ))}
                    </div>
                ) : (
                    articles.map((article, i) => (
                        <ArticleCard key={article.id} article={article} index={i} />
                    ))
                )}
            </div>
        </ClientShell>
    );
}
