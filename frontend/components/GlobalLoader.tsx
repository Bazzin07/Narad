"use client";

import React, { useEffect, useState, Suspense } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { useFrontendContext } from "@/app/contexts/FrontendContext";

function LoaderCore({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { isGlobalLoading, setGlobalLoading } = useFrontendContext();
  const [minTimePassed, setMinTimePassed] = useState(false);

  useEffect(() => {
    // On route change, start loading sequence
    setGlobalLoading(true);
    setMinTimePassed(false);
    
    // Minimum 1.5s delay so the SVG animation isn't just a brief flicker
    const timer = setTimeout(() => {
      setMinTimePassed(true);
    }, 1500);

    // Failsafe: if page doesn't clear loading state within 5s (e.g. static server component), clear it
    const failsafe = setTimeout(() => {
      setGlobalLoading(false);
    }, 5000);

    return () => {
      clearTimeout(timer);
      clearTimeout(failsafe);
    };
  }, [pathname, searchParams, setGlobalLoading]);

  const showLoader = isGlobalLoading || !minTimePassed;

  return (
    <>
      {showLoader && (
        <div className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-white">
          {/* Animated Connecting Graph SVG */}
          <div className="relative flex items-center justify-center mb-10 w-48 h-48">
            <svg
              className="absolute w-full h-full"
              viewBox="0 0 200 200"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Connecting Lines */}
              <g stroke="#628DD3" strokeWidth="2" strokeOpacity="0.4" strokeLinecap="round">
                {/* Center to Top Left */}
                <line x1="100" y1="100" x2="50" y2="40" className="animate-[pulse_1.5s_ease-in-out_infinite]" />
                {/* Center to Top Right */}
                <line x1="100" y1="100" x2="160" y2="60" className="animate-[pulse_2s_ease-in-out_infinite]" />
                {/* Center to Bottom Left */}
                <line x1="100" y1="100" x2="40" y2="150" className="animate-[pulse_1.8s_ease-in-out_infinite]" />
                {/* Center to Bottom Right */}
                <line x1="100" y1="100" x2="150" y2="160" className="animate-[pulse_2.2s_ease-in-out_infinite]" />
                {/* Outer connections */}
                <line x1="50" y1="40" x2="160" y2="60" strokeDasharray="4 4" className="animate-[pulse_3s_ease-in-out_infinite]" />
                <line x1="40" y1="150" x2="150" y2="160" strokeDasharray="4 4" className="animate-[pulse_3s_ease-in-out_infinite]" />
              </g>

              {/* Nodes */}
              {/* Center Node */}
              <circle cx="100" cy="100" r="12" fill="#FAB33B" className="animate-pulse" />
              <circle cx="100" cy="100" r="16" stroke="#FAB33B" strokeWidth="2" strokeOpacity="0.5" className="animate-[ping_2s_ease-in-out_infinite]" />
              
              {/* Peripheral Nodes */}
              <circle cx="50" cy="40" r="6" fill="#628DD3" className="animate-pulse" style={{ animationDelay: '0.2s' }} />
              <circle cx="160" cy="60" r="8" fill="#111111" className="animate-bounce" style={{ animationDelay: '0.5s' }} />
              <circle cx="40" cy="150" r="7" fill="#DDA5A1" className="animate-pulse" style={{ animationDelay: '0.1s' }} />
              <circle cx="150" cy="160" r="5" fill="#628DD3" className="animate-bounce" style={{ animationDelay: '0.4s' }} />
            </svg>
          </div>

          {/* Loading Text */}
          <div className="flex flex-col items-center">
            <h2 className="text-2xl font-semibold tracking-widest text-[#111111] uppercase font-headline">
              Narad
            </h2>
            <div className="flex items-center mt-4 space-x-1">
              <p className="text-xs tracking-[0.2em] font-mono text-[#628DD3] uppercase font-medium">
                Synthesizing Connections
              </p>
              <span className="flex space-x-[2px] ml-2">
                <span className="w-1.5 h-1.5 bg-[#FAB33B] rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-1.5 h-1.5 bg-[#FAB33B] rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-1.5 h-1.5 bg-[#FAB33B] rounded-full animate-bounce"></span>
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Actual Page Content renders normally behind the solid white fixed splash screen */}
      {children}
    </>
  );
}

export default function GlobalLoader({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="min-h-screen bg-white" />}>
      <LoaderCore>{children}</LoaderCore>
    </Suspense>
  );
}
