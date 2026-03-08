"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import ClientShell from "../components/ClientShell";
import { getTopics, type TopicCount } from "../lib/api";

const TOPIC_ICONS: Record<string, string> = {
    military: "⚔",
    energy: "⚡",
    politics: "🏛",
    health: "🏥",
    technology: "⬡",
    economy: "◈",
    diplomacy: "◎",
    terrorism: "⚠",
    environment: "◉",
    general: "▣",
};

export default function TopicsPage() {
    const [language, setLanguage] = useState("all");
    const [topics, setTopics] = useState<TopicCount[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getTopics()
            .then((data) => setTopics(data.topics))
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    const totalArticles = topics.reduce((sum, t) => sum + t.count, 0);

    return (
        <ClientShell language={language} onLanguageChange={setLanguage}>
            <div style={{ padding: "2rem var(--page-gutter) 4rem" }}>
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-10"
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
                        Classification
                    </span>
                    <h1
                        style={{
                            fontFamily: "var(--font-headline)",
                            fontSize: "clamp(2rem, 4vw, 3rem)",
                            fontWeight: 600,
                            margin: 0,
                        }}
                    >
                        Topic Clusters
                    </h1>
                    <p
                        className="mt-2"
                        style={{
                            fontFamily: "var(--font-body)",
                            fontSize: "0.85rem",
                            color: "var(--text-secondary)",
                        }}
                    >
                        {totalArticles} events classified across {topics.length} domains
                    </p>
                </motion.div>

                {/* Grid */}
                {loading ? (
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                        {[...Array(8)].map((_, i) => (
                            <div
                                key={i}
                                className="animate-pulse"
                                style={{
                                    height: "160px",
                                    background: "var(--bg-elevated)",
                                    border: "1px solid var(--border-subtle)",
                                }}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                        {topics.map((topic, i) => (
                            <motion.div
                                key={topic.topic}
                                initial={{ opacity: 0, y: 12 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.06 }}
                            >
                                <Link
                                    href={`/topics/${topic.topic}`}
                                    className="block no-underline group"
                                    style={{ textDecoration: "none" }}
                                >
                                    <div
                                        className="p-6 transition-all duration-300"
                                        style={{
                                            background: "var(--bg-elevated)",
                                            border: "1px solid var(--border-subtle)",
                                            minHeight: "160px",
                                            display: "flex",
                                            flexDirection: "column",
                                            justifyContent: "space-between",
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.borderColor = "var(--border-accent)";
                                            e.currentTarget.style.boxShadow = "0 0 30px var(--accent-glow)";
                                            e.currentTarget.style.transform = "scale(1.02)";
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.borderColor = "var(--border-subtle)";
                                            e.currentTarget.style.boxShadow = "none";
                                            e.currentTarget.style.transform = "scale(1)";
                                        }}
                                    >
                                        <div>
                                            <span
                                                className="block mb-3"
                                                style={{
                                                    fontSize: "1.5rem",
                                                    opacity: 0.6,
                                                    filter: "grayscale(100%)",
                                                }}
                                            >
                                                {TOPIC_ICONS[topic.topic] || "▣"}
                                            </span>
                                            <h3
                                                className="m-0"
                                                style={{
                                                    fontFamily: "var(--font-headline)",
                                                    fontSize: "1rem",
                                                    fontWeight: 600,
                                                    textTransform: "capitalize",
                                                    color: "var(--text-primary)",
                                                }}
                                            >
                                                {topic.topic}
                                            </h3>
                                        </div>
                                        <div className="flex items-end justify-between mt-4">
                                            <span
                                                style={{
                                                    fontFamily: "var(--font-mono)",
                                                    fontSize: "1.5rem",
                                                    fontWeight: 600,
                                                    color: "var(--text-primary)",
                                                }}
                                            >
                                                {topic.count}
                                            </span>
                                            <span
                                                style={{
                                                    fontFamily: "var(--font-mono)",
                                                    fontSize: "0.6rem",
                                                    color: "var(--text-dim)",
                                                    letterSpacing: "0.05em",
                                                }}
                                            >
                                                EVENTS
                                            </span>
                                        </div>
                                    </div>
                                </Link>
                            </motion.div>
                        ))}
                    </div>
                )}
            </div>
        </ClientShell>
    );
}
