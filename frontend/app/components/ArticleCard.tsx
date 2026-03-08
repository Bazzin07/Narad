"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import type { ArticleSummary } from "../lib/api";

interface ArticleCardProps {
    article: ArticleSummary;
    index: number;
    isNew?: boolean;
}

function timeAgo(dateStr: string | null): string {
    if (!dateStr) return "";
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

export default function ArticleCard({ article, index, isNew }: ArticleCardProps) {
    const entities = article.entities || [];
    const hasImage = !!article.image_url;

    return (
        <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.03, duration: 0.3 }}
        >
            <Link
                href={`/article/${article.id}`}
                className="block no-underline group"
                style={{ textDecoration: "none" }}
            >
                <article
                    className="py-5 transition-all duration-200"
                    style={{
                        borderBottom: "1px solid var(--border-subtle)",
                    }}
                >
                    <div style={{
                        display: "flex",
                        gap: "1rem",
                        alignItems: "flex-start",
                    }}>
                        {/* Text Column */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                            {/* Meta row */}
                            <div className="flex items-center gap-2 mb-2 flex-wrap">
                                {isNew && (
                                    <span
                                        style={{
                                            fontFamily: "var(--font-mono)",
                                            fontSize: "0.55rem",
                                            letterSpacing: "0.1em",
                                            color: "#FFFFFF",
                                            background: "var(--accent)",
                                            padding: "1px 6px",
                                            textTransform: "uppercase",
                                            fontWeight: 600,
                                        }}
                                    >
                                        NEW
                                    </span>
                                )}
                                <span
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: "0.65rem",
                                        letterSpacing: "0.05em",
                                        color: "var(--text-muted)",
                                        fontWeight: 500,
                                    }}
                                >
                                    {article.source}
                                </span>

                                <span
                                    style={{
                                        width: "3px",
                                        height: "3px",
                                        borderRadius: "50%",
                                        background: "var(--text-dim)",
                                        display: "inline-block",
                                    }}
                                />

                                <span
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: "0.6rem",
                                        color: "var(--text-dim)",
                                    }}
                                >
                                    {timeAgo(article.published_at)}
                                </span>

                                {article.topic && article.topic !== "general" && (
                                    <>
                                        <span
                                            style={{
                                                width: "3px",
                                                height: "3px",
                                                borderRadius: "50%",
                                                background: "var(--text-dim)",
                                                display: "inline-block",
                                            }}
                                        />
                                        <span
                                            style={{
                                                fontFamily: "var(--font-mono)",
                                                fontSize: "0.55rem",
                                                letterSpacing: "0.06em",
                                                textTransform: "uppercase",
                                                color: "var(--accent)",
                                                opacity: 0.8,
                                            }}
                                        >
                                            {article.topic}
                                        </span>
                                    </>
                                )}
                            </div>

                            {/* Title */}
                            <h3
                                className="m-0 transition-colors duration-200"
                                style={{
                                    fontFamily: "var(--font-headline)",
                                    fontSize: "1.05rem",
                                    fontWeight: 500,
                                    lineHeight: 1.35,
                                    color: "var(--text-primary)",
                                }}
                            >
                                <span
                                    style={{ transition: "color 0.2s ease" }}
                                    className="group-hover:!text-[var(--accent)]"
                                >
                                    {article.title}
                                </span>
                            </h3>

                            {/* Read more hint on hover */}
                            <div
                                className="mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                            >
                                <span
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: "0.6rem",
                                        color: "var(--accent)",
                                        opacity: 0.7,
                                    }}
                                >
                                    Read full article →
                                </span>
                            </div>
                        </div>

                        {/* Image Column */}
                        {hasImage && (
                            <div
                                style={{
                                    width: "140px",
                                    height: "90px",
                                    flexShrink: 0,
                                    overflow: "hidden",
                                    borderRadius: "4px",
                                    border: "1px solid var(--border-subtle)",
                                    marginTop: "4px",
                                }}
                            >
                                <img
                                    src={article.image_url!}
                                    alt=""
                                    style={{
                                        width: "100%",
                                        height: "100%",
                                        objectFit: "cover",
                                        display: "block",
                                        transition: "transform 0.3s ease",
                                    }}
                                    className="group-hover:scale-105"
                                    onError={(e) => {
                                        (e.target as HTMLImageElement).parentElement!.style.display = "none";
                                    }}
                                />
                            </div>
                        )}
                    </div>
                </article>
            </Link>
        </motion.div>
    );
}
