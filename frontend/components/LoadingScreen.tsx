"use client";

import React, { useEffect, useState } from "react";

export default function LoadingScreen() {
  return (
    <div className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-white">
      {/* Animated SVG Graphic */}
      <div className="relative flex items-center justify-center mb-8">
        {/* Outer rotating ring */}
        <svg
          className="absolute w-32 h-32 animate-[spin_4s_linear_infinite]"
          viewBox="0 0 100 100"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle
            cx="50"
            cy="50"
            r="48"
            stroke="url(#gradientRing)"
            strokeWidth="1.5"
            strokeDasharray="40 20"
            strokeLinecap="round"
          />
          <defs>
            <linearGradient id="gradientRing" x1="0" y1="0" x2="100" y2="100">
              <stop offset="0%" stopColor="#628DD3" stopOpacity="0" />
              <stop offset="50%" stopColor="#628DD3" stopOpacity="1" />
              <stop offset="100%" stopColor="#FAB33B" stopOpacity="0" />
            </linearGradient>
          </defs>
        </svg>

        {/* Inner reverse rotating dashed ring */}
        <svg
          className="absolute w-24 h-24 animate-[spin_3s_linear_infinite_reverse]"
          viewBox="0 0 100 100"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle
            cx="50"
            cy="50"
            r="46"
            stroke="#111111"
            strokeWidth="1"
            strokeDasharray="5 5"
            strokeOpacity="0.15"
          />
        </svg>

        {/* Central pulsating core */}
        <div className="relative flex items-center justify-center w-12 h-12">
          <div className="absolute w-full h-full bg-[#628DD3] rounded-full animate-ping opacity-60"></div>
          <div className="relative w-4 h-4 bg-[#628DD3] rounded-full"></div>
        </div>
      </div>

      {/* Loading Text */}
      <div className="flex flex-col items-center">
        <h2 className="text-xl font-semibold tracking-widest text-[#111111] uppercase font-headline">
          Narad
        </h2>
        <div className="flex items-center mt-3 space-x-1">
          <p className="text-xs tracking-[0.2em] font-mono text-[#DDA5A1] uppercase">
            Establishing Link
          </p>
          <span className="flex space-x-[2px] ml-1">
            <span className="w-1 h-1 bg-[#628DD3] rounded-full animate-bounce [animation-delay:-0.3s]"></span>
            <span className="w-1 h-1 bg-[#628DD3] rounded-full animate-bounce [animation-delay:-0.15s]"></span>
            <span className="w-1 h-1 bg-[#628DD3] rounded-full animate-bounce"></span>
          </span>
        </div>
      </div>
    </div>
  );
}
