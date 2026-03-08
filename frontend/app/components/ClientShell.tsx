"use client";

import { useState } from "react";
import Navbar from "./Navbar";
import SearchOverlay from "./SearchOverlay";

interface ClientShellProps {
    children: React.ReactNode;
    language: string;
    onLanguageChange: (lang: string) => void;
}

export default function ClientShell({ children, language, onLanguageChange }: ClientShellProps) {
    const [searchOpen, setSearchOpen] = useState(false);

    return (
        <>
            <Navbar
                language={language}
                onLanguageChange={onLanguageChange}
                onSearchOpen={() => setSearchOpen(true)}
            />
            <SearchOverlay isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
            <main className="pt-14">{children}</main>
        </>
    );
}
