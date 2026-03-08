"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavbarProps {
    onSearchOpen: () => void;
    language: string;
    onLanguageChange: (lang: string) => void;
}

const NAV_LINKS = [
    { label: "India", href: "/" },
    { label: "Command Center", href: "/india" },
    { label: "World", href: "/global" },
    { label: "Topics", href: "/topics" },
    { label: "Probe", href: "/probe" },
];

const LANGUAGES = [
    { code: "all", label: "ALL" },
    { code: "en", label: "EN" },
    { code: "hi", label: "HI" },
    { code: "ta", label: "TA" },
    { code: "bn", label: "BN" },
    { code: "te", label: "TE" },
    { code: "mr", label: "MR" },
    { code: "gu", label: "GU" },
    { code: "kn", label: "KN" },
    { code: "ml", label: "ML" },
];

export default function Navbar({ onSearchOpen, language, onLanguageChange }: NavbarProps) {
    const pathname = usePathname();
    const [scrolled, setScrolled] = useState(false);
    const [langOpen, setLangOpen] = useState(false);

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 20);
        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    return (
        <motion.nav
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
            style={{
                background: "rgba(255, 255, 255, 0.97)",
                backdropFilter: "blur(12px)",
                borderBottom: "1px solid var(--border-subtle)",
                boxShadow: scrolled ? "0 1px 0 var(--border-visible)" : "none",
            }}
        >
            <div
                className="flex items-center justify-between"
                style={{
                    padding: "0 var(--page-gutter)",
                    height: "56px",
                }}
            >
                {/* Left — Wordmark */}
                <Link href="/" className="no-underline flex items-center gap-2" style={{ textDecoration: "none" }}>
                    <span
                        style={{
                            fontFamily: "var(--font-headline)",
                            fontSize: "1.1rem",
                            fontWeight: 700,
                            letterSpacing: "0.08em",
                            color: "var(--text-primary)",
                        }}
                    >
                        NARAD
                    </span>
                    <span
                        style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.55rem",
                            letterSpacing: "0.12em",
                            color: "var(--accent)",
                            fontWeight: 500,
                        }}
                    >
                        INTELLIGENCE
                    </span>
                </Link>

                {/* Center — Navigation */}
                <div className="hidden md:flex items-center gap-1">
                    {NAV_LINKS.map((link) => {
                        const isActive = pathname === link.href ||
                            (link.href !== "/" && pathname.startsWith(link.href));
                        return (
                            <Link
                                key={link.href}
                                href={link.href}
                                className="no-underline relative px-4 py-1.5"
                                style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: "0.7rem",
                                    letterSpacing: "0.1em",
                                    textTransform: "uppercase",
                                    textDecoration: "none",
                                    color: isActive ? "var(--text-primary)" : "var(--text-muted)",
                                    fontWeight: isActive ? 600 : 400,
                                    transition: "color 0.2s ease",
                                }}
                            >
                                {link.label}
                                {isActive && (
                                    <motion.div
                                        layoutId="nav-indicator"
                                        className="absolute bottom-0 left-4 right-4"
                                        style={{
                                            height: "1.5px",
                                            background: "var(--accent)",
                                        }}
                                        transition={{ type: "spring", stiffness: 400, damping: 30 }}
                                    />
                                )}
                            </Link>
                        );
                    })}
                </div>

                {/* Right — Search + Language + Live */}
                <div className="flex items-center gap-4">
                    {/* Search trigger */}
                    <button
                        onClick={onSearchOpen}
                        className="flex items-center gap-2 px-3 py-1.5 cursor-pointer transition-all duration-200"
                        style={{
                            background: "transparent",
                            border: "1px solid var(--border-subtle)",
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.65rem",
                            color: "var(--text-muted)",
                            letterSpacing: "0.05em",
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = "var(--border-visible)";
                            e.currentTarget.style.color = "var(--text-secondary)";
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = "var(--border-subtle)";
                            e.currentTarget.style.color = "var(--text-muted)";
                        }}
                    >
                        <span style={{ opacity: 0.6 }}>⌕</span>
                        Search
                        <span
                            className="hidden sm:inline"
                            style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "0.55rem",
                                color: "var(--text-dim)",
                                border: "1px solid var(--border-subtle)",
                                padding: "1px 5px",
                                marginLeft: "4px",
                            }}
                        >
                            ⌘K
                        </span>
                    </button>

                    {/* Language selector */}
                    <div className="relative">
                        <button
                            onClick={() => setLangOpen(!langOpen)}
                            className="flex items-center gap-1 cursor-pointer px-2 py-1 transition-colors"
                            style={{
                                background: "transparent",
                                border: "1px solid var(--border-subtle)",
                                fontFamily: "var(--font-mono)",
                                fontSize: "0.65rem",
                                color: "var(--text-secondary)",
                                letterSpacing: "0.08em",
                            }}
                        >
                            {LANGUAGES.find((l) => l.code === language)?.label || "ALL"}
                            <span style={{ fontSize: "0.5rem", marginLeft: "2px" }}>▼</span>
                        </button>

                        {langOpen && (
                            <motion.div
                                initial={{ opacity: 0, y: -4 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="absolute right-0 top-full mt-1 z-50"
                                style={{
                                    background: "var(--bg-deep)",
                                    border: "1px solid var(--border-subtle)",
                                    boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
                                    minWidth: "70px",
                                }}
                            >
                                {LANGUAGES.map((lang) => (
                                    <button
                                        key={lang.code}
                                        onClick={() => {
                                            onLanguageChange(lang.code);
                                            setLangOpen(false);
                                        }}
                                        className="w-full text-left px-3 py-1.5 cursor-pointer transition-colors"
                                        style={{
                                            background: language === lang.code ? "var(--accent-dim)" : "transparent",
                                            border: "none",
                                            fontFamily: "var(--font-mono)",
                                            fontSize: "0.6rem",
                                            color: language === lang.code ? "var(--accent)" : "var(--text-secondary)",
                                            letterSpacing: "0.08em",
                                        }}
                                    >
                                        {lang.label}
                                    </button>
                                ))}
                            </motion.div>
                        )}
                    </div>

                    {/* Live indicator */}
                    <div className="hidden sm:flex items-center gap-2">
                        <div
                            className="live-dot"
                            style={{
                                width: "6px",
                                height: "6px",
                                borderRadius: "50%",
                                background: "var(--accent)",
                            }}
                        />
                        <span
                            style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "0.55rem",
                                letterSpacing: "0.08em",
                                color: "var(--text-muted)",
                                textTransform: "uppercase",
                            }}
                        >
                            Live
                        </span>
                    </div>
                </div>
            </div>
        </motion.nav>
    );
}
