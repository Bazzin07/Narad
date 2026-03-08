"use client";

import { motion } from "framer-motion";
import type { TopicCount } from "../lib/api";

interface ConnectionPulseProps {
    topics: TopicCount[];
    totalArticles: number;
}

export default function ConnectionPulse({ topics, totalArticles }: ConnectionPulseProps) {
    const maxCount = Math.max(...topics.map((t) => t.count), 1);

    return (
        <div>
            {/* Header */}
            <div className="flex items-center gap-2 mb-6">
                <div
                    className="w-2 h-2 rounded-full pulse-dot"
                    style={{ background: "var(--accent)" }}
                />
                <span
                    style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.7rem",
                        letterSpacing: "0.1em",
                        textTransform: "uppercase",
                        color: "var(--text-muted)",
                    }}
                >
                    Intelligence Pulse
                </span>
            </div>

            {/* Stats */}
            <div
                className="mb-6 p-4"
                style={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border-subtle)",
                }}
            >
                <div className="flex items-baseline gap-2">
                    <span
                        style={{
                            fontFamily: "var(--font-headline)",
                            fontSize: "2rem",
                            fontWeight: 700,
                            color: "var(--text-primary)",
                        }}
                    >
                        {totalArticles}
                    </span>
                    <span
                        style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.65rem",
                            color: "var(--text-muted)",
                            letterSpacing: "0.05em",
                        }}
                    >
                        EVENTS TRACKED
                    </span>
                </div>
                <div className="mt-2 flex items-center gap-2">
                    <span
                        style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.65rem",
                            color: "var(--text-dim)",
                        }}
                    >
                        {topics.length} TOPIC CLUSTERS
                    </span>
                </div>
            </div>

            {/* Topic Distribution */}
            <div className="mb-6">
                <span
                    className="block mb-3"
                    style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.65rem",
                        letterSpacing: "0.1em",
                        textTransform: "uppercase",
                        color: "var(--text-muted)",
                    }}
                >
                    Topic Distribution
                </span>
                <div className="space-y-3">
                    {topics
                        .filter((t) => t.topic !== "general")
                        .slice(0, 8)
                        .map((topic, i) => (
                            <motion.div
                                key={topic.topic}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.2 + i * 0.05 }}
                            >
                                <div className="flex items-center justify-between mb-1">
                                    <span
                                        style={{
                                            fontFamily: "var(--font-mono)",
                                            fontSize: "0.65rem",
                                            letterSpacing: "0.05em",
                                            textTransform: "uppercase",
                                            color: "var(--text-secondary)",
                                        }}
                                    >
                                        {topic.topic}
                                    </span>
                                    <span
                                        style={{
                                            fontFamily: "var(--font-mono)",
                                            fontSize: "0.6rem",
                                            color: "var(--text-dim)",
                                        }}
                                    >
                                        {topic.count}
                                    </span>
                                </div>
                                <div
                                    style={{
                                        height: "2px",
                                        background: "var(--bg-surface)",
                                        width: "100%",
                                    }}
                                >
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${(topic.count / maxCount) * 100}%` }}
                                        transition={{ delay: 0.3 + i * 0.05, duration: 0.6, ease: "easeOut" }}
                                        style={{
                                            height: "2px",
                                            background: "var(--accent)",
                                        }}
                                    />
                                </div>
                            </motion.div>
                        ))}
                </div>
            </div>

            {/* System status */}
            <div
                className="p-4"
                style={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border-subtle)",
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
                    System Status
                </span>
                <div className="space-y-1">
                    {[
                        { label: "DATABASE", status: "CONNECTED", ok: true },
                        { label: "FAISS INDEX", status: "203 VECTORS", ok: true },
                        { label: "LLM BACKEND", status: "MOCK", ok: true },
                    ].map((item) => (
                        <div key={item.label} className="flex items-center justify-between">
                            <span
                                style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: "0.6rem",
                                    color: "var(--text-muted)",
                                }}
                            >
                                {item.label}
                            </span>
                            <span
                                className="flex items-center gap-1"
                                style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: "0.55rem",
                                    color: item.ok ? "#4ADE80" : "var(--accent)",
                                }}
                            >
                                <span
                                    className="inline-block w-1.5 h-1.5 rounded-full"
                                    style={{ background: item.ok ? "#4ADE80" : "var(--accent)" }}
                                />
                                {item.status}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
