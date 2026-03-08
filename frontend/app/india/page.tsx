"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from "react-simple-maps";
// @ts-ignore
import { Marker } from "react-simple-maps";
import {
  getDashboardHeatmap,
  getAIBriefing,
  getMarketData,
  getStateData,
  getRegionalAnalytics,
  getDomainRadar,
  getSituationRoom,
  getNarrativeConflicts,
  askNarad,
  getMapMarkers,
  type MapMarker,
  type StateHeatmapEntry,
  type AIBriefingResponse,
  type MarketData,
  type RegionalAnalyticsResponse,
  type DomainRadarResponse,
  type SituationRoomResponse,
  type NarrativeConflictsResponse,
  type AskNaradResponse,
  type AskNaradSource,
} from "../lib/api";
import Navbar from "../components/Navbar";

// ── Working GeoJSON for India states ────────────────────────────────
const INDIA_GEO =
  "https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112/raw/e388c4cae20aa53cb5090210a42ebb9b765c0a36/india_states.geojson";

// ── State mapping ───────────────────────────────────────────────────
const STATE_NAME_MAP: Record<string, string> = {
  "Delhi": "delhi", "NCT of Delhi": "delhi",
  "Maharashtra": "maharashtra", "Karnataka": "karnataka",
  "Tamil Nadu": "tamil_nadu", "Telangana": "telangana", "Telengana": "telangana",
  "Uttar Pradesh": "uttar_pradesh", "West Bengal": "west_bengal",
  "Rajasthan": "rajasthan", "Gujarat": "gujarat",
  "Madhya Pradesh": "madhya_pradesh", "Kerala": "kerala",
  "Bihar": "bihar", "Punjab": "punjab", "Haryana": "haryana",
  "Odisha": "odisha", "Orissa": "odisha",
  "Assam": "assam", "Jharkhand": "jharkhand",
  "Chhattisgarh": "chhattisgarh", "Uttarakhand": "uttarakhand",
  "Himachal Pradesh": "himachal_pradesh", "Goa": "goa",
  "Jammu & Kashmir": "jammu_and_kashmir", "Jammu and Kashmir": "jammu_and_kashmir",
  "Andhra Pradesh": "andhra_pradesh", "Ladakh": "ladakh",
  "Tripura": "tripura", "Meghalaya": "meghalaya",
  "Manipur": "manipur", "Mizoram": "mizoram", "Nagaland": "nagaland",
  "Arunachal Pradesh": "arunachal_pradesh", "Sikkim": "sikkim",
  "Puducherry": "puducherry", "Pondicherry": "puducherry",
  "Andaman and Nicobar Islands": "andaman_nicobar", "Andaman & Nicobar Island": "andaman_nicobar",
  "Chandigarh": "chandigarh", "Lakshadweep": "lakshadweep",
  "Dadra and Nagar Haveli and Daman and Diu": "dadra_daman",
  "Daman and Diu": "dadra_daman", "Dadra and Nagar Haveli": "dadra_daman",
  "The Government of NCT of Delhi": "delhi",
};

const STATE_DISPLAY: Record<string, string> = {
  delhi: "Delhi", maharashtra: "Maharashtra", karnataka: "Karnataka",
  tamil_nadu: "Tamil Nadu", telangana: "Telangana", uttar_pradesh: "Uttar Pradesh",
  west_bengal: "West Bengal", rajasthan: "Rajasthan", gujarat: "Gujarat",
  madhya_pradesh: "Madhya Pradesh", kerala: "Kerala", bihar: "Bihar",
  punjab: "Punjab", haryana: "Haryana", odisha: "Odisha", assam: "Assam",
  jharkhand: "Jharkhand", chhattisgarh: "Chhattisgarh", uttarakhand: "Uttarakhand",
  himachal_pradesh: "Himachal Pradesh", goa: "Goa",
  jammu_and_kashmir: "Jammu & Kashmir", andhra_pradesh: "Andhra Pradesh",
  ladakh: "Ladakh", tripura: "Tripura", meghalaya: "Meghalaya",
  manipur: "Manipur", mizoram: "Mizoram", nagaland: "Nagaland",
  arunachal_pradesh: "Arunachal Pradesh", sikkim: "Sikkim", puducherry: "Puducherry",
};
const ALL_STATES = Object.keys(STATE_DISPLAY);

// ── News Channels ───────────────────────────────────────────────────
const NEWS_CHANNELS = [
  { id: "ndtv", name: "NDTV", embed: "https://www.youtube.com/embed/CkgJ_PWLcPM?autoplay=0&mute=1" },
  { id: "timesnow", name: "TIMES NOW", embed: "https://www.youtube.com/embed/-uLJfqSsX6M?autoplay=0&mute=1" },
  { id: "indiatoday", name: "INDIA TODAY", embed: "https://www.youtube.com/embed/kZLaSDu4_Og?autoplay=0&mute=1" },
  { id: "republic", name: "REPUBLIC", embed: "https://www.youtube.com/embed/8ZVRCUccRLw?autoplay=0&mute=1" },
  { id: "abpnews", name: "ABP", embed: "https://www.youtube.com/embed/uu1hjwO1D7A?autoplay=0&mute=1" },
  { id: "news18", name: "NEWS18", embed: "https://www.youtube.com/embed/TvAV58jMUHo?autoplay=0&mute=1" },
  { id: "wion", name: "WION", embed: "https://www.youtube.com/embed/hOO35m5eGeg?autoplay=0&mute=1" },
  { id: "ddnews", name: "DD NEWS", embed: "https://www.youtube.com/embed/Et1rjUJFqrs?autoplay=0&mute=1" },
];

// ── Helpers ─────────────────────────────────────────────────────────
function sentimentColor(v: number) {
  if (v > 0.15) return "#628DD3"; if (v > 0.05) return "#628DD3"; // Blue
  if (v < -0.15) return "#DDA5A1"; if (v < -0.05) return "#CA8076"; // Peach/Red
  return "var(--text-muted)";
}
function sentimentLabel(v: number) {
  if (v > 0.15) return "Positive"; if (v > 0.05) return "+ve";
  if (v < -0.15) return "Negative"; if (v < -0.05) return "-ve";
  return "Neutral";
}
function heatFill(s: number, c: number) {
  if (c === 0) return "var(--bg-surface)"; // White/light gray base
  if (s > 0.15) return "#628DD3"; if (s > 0.05) return "rgba(98, 141, 211, 0.5)"; 
  if (s < -0.15) return "#DDA5A1"; if (s < -0.05) return "rgba(202, 128, 118, 0.5)";
  return "var(--bg-hover)";
}

function Sparkline({ data, color, w = 55, h = 16 }: { data: number[]; color: string; w?: number; h?: number }) {
  if (!data.length) return null;
  const mn = Math.min(...data), mx = Math.max(...data), r = mx - mn || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - mn) / r) * h}`).join(" ");
  return <svg width={w} height={h} style={{ display: "block" }}><polyline fill="none" stroke={color} strokeWidth="1.5" points={pts} /></svg>;
}

// ── Domain Radar SVG ─────────────────────────────────────────────────
function DomainRadar({ domains }: { domains: Record<string, { sentiment: number; article_count: number }> }) {
  const labels = Object.keys(domains);
  const N = labels.length;
  if (N === 0) return null;
  const cx = 70, cy = 70, R = 55;
  const angleStep = (2 * Math.PI) / N;
  // Map sentiment [-1,1] to radius [0, R]
  const sentToR = (s: number) => ((s + 1) / 2) * R;
  const toXY = (angle: number, r: number) => ({
    x: cx + r * Math.sin(angle),
    y: cy - r * Math.cos(angle),
  });
  // Grid rings
  const rings = [0.25, 0.5, 0.75, 1];
  // Polygon points from data
  const points = labels.map((l, i) => {
    const s = domains[l]?.sentiment ?? 0;
    const r = sentToR(Math.max(-1, Math.min(1, s)));
    const { x, y } = toXY(i * angleStep, r);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  return (
    <svg width={110} height={110} viewBox="0 0 140 140" style={{ overflow: "visible", display: "block" }}>
      {/* Grid */}
      {rings.map(ring =>
        <polygon key={ring}
          points={labels.map((_, i) => { const { x, y } = toXY(i * angleStep, R * ring); return `${x.toFixed(1)},${y.toFixed(1)}`; }).join(" ")}
          fill="none" stroke="var(--border-subtle)" strokeWidth="0.5" />
      )}
      {/* Axes */}
      {labels.map((_, i) => {
        const { x, y } = toXY(i * angleStep, R);
        return <line key={i} x1={cx} y1={cy} x2={x.toFixed(1)} y2={y.toFixed(1)} stroke="var(--border-subtle)" strokeWidth="0.5" />;
      })}
      {/* Data polygon */}
      <polygon points={points} fill="rgba(98, 141, 211, 0.08)" stroke="#628DD3" strokeWidth="1.5" />
      {/* Labels */}
      {labels.map((l, i) => {
        const { x, y } = toXY(i * angleStep, R + 10);
        const anchor = x < cx - 5 ? "end" : x > cx + 5 ? "start" : "middle";
        return (
          <text key={i} x={x.toFixed(1)} y={y.toFixed(1)}
            textAnchor={anchor} dominantBaseline="middle"
            style={{ fontFamily: "var(--font-mono)", fontSize: "5px", fill: "var(--text-dim)" }}>
            {l}
          </text>
        );
      })}
      {/* Center dot */}
      <circle cx={cx} cy={cy} r={2} fill="#628DD3" />
    </svg>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <div style={{
      fontFamily: "var(--font-mono)", fontSize: "0.5rem", letterSpacing: "0.12em",
      textTransform: "uppercase", color: "var(--text-dim)",
      marginBottom: "0.4rem", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.25rem",
    }}>{children}</div>
  );
}

function IntelCard({ icon, category, summary, impact }: { icon: string; category: string; summary: string; impact: "high" | "medium" | "low" }) {
  const colors = { high: "#DDA5A1", medium: "#FAB33B", low: "#628DD3" };
  return (
    <div style={{ padding: "0.45rem 0.5rem", background: "var(--bg-deep)", borderBottom: "1px solid var(--border-subtle)", display: "flex", gap: "0.4rem", alignItems: "flex-start" }}>
      <span style={{ fontSize: "0.85rem" }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.4rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-dim)" }}>{category}</div>
        <div style={{ fontFamily: "var(--font-body)", fontSize: "0.68rem", color: "var(--text-primary)", lineHeight: 1.3, marginTop: "0.05rem" }}>{summary}</div>
      </div>
      <span style={{
        fontFamily: "var(--font-mono)", fontSize: "0.38rem", fontWeight: 700,
        color: colors[impact], textTransform: "uppercase", letterSpacing: "0.06em",
        padding: "0.08rem 0.2rem", border: `1px solid ${colors[impact]}30`, background: `${colors[impact]}08`,
        whiteSpace: "nowrap",
      }}>{impact}</span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// NEW COMPONENTS
// ═══════════════════════════════════════════════════════════════════
function TypingEffect({ text, speed = 8 }: { text: string; speed?: number }) {
  const [displayedText, setDisplayedText] = useState("");
  
  useEffect(() => {
    let i = 0;
    setDisplayedText("");
    const interval = setInterval(() => {
      setDisplayedText((prev) => prev + (text.charAt(i) || ""));
      i++;
      if (i >= text.length) clearInterval(interval);
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed]);

  return <>{displayedText}</>;
}

// ═══════════════════════════════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════════════════════════════
export default function IndiaIntelligence() {
  const [selectedState, setSelectedState] = useState<string | null>(null);
  const [heatmapData, setHeatmapData] = useState<StateHeatmapEntry[]>([]);
  const [briefing, setBriefing] = useState<AIBriefingResponse | null>(null);
  const [briefingLoading, setBriefingLoading] = useState(false);
  const [markets, setMarkets] = useState<MarketData | null>(null);
  const [stateData, setStateData] = useState<Record<string, Record<string, string>>>({});
  const [hoveredState, setHoveredState] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [regionalAnalytics, setRegionalAnalytics] = useState<RegionalAnalyticsResponse | null>(null);
  const [domainRadar, setDomainRadar] = useState<DomainRadarResponse | null>(null);
  const [situationRoom, setSituationRoom] = useState<SituationRoomResponse | null>(null);
  const [situationRoomLoading, setSituationRoomLoading] = useState(false);
  const [conflicts, setConflicts] = useState<NarrativeConflictsResponse | null>(null);
  const [askQuestion, setAskQuestion] = useState("");
  const [askLoading, setAskLoading] = useState(false);
  const [askHistory, setAskHistory] = useState<Array<{ q: string; r: AskNaradResponse }>>([]);
  const askEndRef = useRef<HTMLDivElement>(null);
  const [rightTab, setRightTab] = useState<"analytics"|"radar"|"brief"|"conflicts"|"ask">("analytics");
  const [activeChannel, setActiveChannel] = useState("ndtv");
  const [channelModalOpen, setChannelModalOpen] = useState(false);
  const [enabledChannels, setEnabledChannels] = useState<string[]>(["ndtv", "timesnow", "indiatoday", "republic", "abpnews"]);
  const [activeOverlays, setActiveOverlays] = useState<Set<string>>(new Set());
  const [mapMarkers, setMapMarkers] = useState<Record<string, MapMarker[]>>({});
  const [showStateOverlay, setShowStateOverlay] = useState(false);

  const toggleOverlay = async (type: string) => {
    const newO = new Set(activeOverlays);
    if (newO.has(type)) {
      newO.delete(type);
    } else {
      newO.add(type);
      if (!mapMarkers[type]) {
        try {
           const res = await getMapMarkers(type);
           setMapMarkers(prev => ({...prev, [type]: res.markers}));
        } catch {}
      }
    }
    setActiveOverlays(newO);
  };

  const heatmapMap = useMemo(() => {
    const m: Record<string, StateHeatmapEntry> = {};
    heatmapData.forEach(h => { m[h.state] = h; });
    return m;
  }, [heatmapData]);

  useEffect(() => {
    getDashboardHeatmap().then(d => setHeatmapData(d.states)).catch(() => {});
    getMarketData().then(setMarkets).catch(() => {});
    getStateData().then(setStateData).catch(() => {});
    getRegionalAnalytics(null).then(setRegionalAnalytics).catch(() => {});
    getDomainRadar(null).then(setDomainRadar).catch(() => {});
    getNarrativeConflicts(null).then(setConflicts).catch(() => {});
    try { const s = localStorage.getItem("narad_channels"); if (s) setEnabledChannels(JSON.parse(s)); } catch { /* */ }
  }, []);

  // Scroll Ask Narad chat to bottom on new answers
  useEffect(() => { askEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [askHistory]);

  const handleAskNarad = async () => {
    const q = askQuestion.trim();
    if (!q || askLoading) return;
    setAskQuestion("");
    setAskLoading(true);
    try {
      const r = await askNarad(q, selectedState);
      setAskHistory(prev => [...prev, { q, r }]);
    } catch {
      setAskHistory(prev => [...prev, { q, r: { answer: "Failed to get answer. Please try again.", sources: [], pages_retrieved: 0, articles_scanned: 0, source: "error" } }]);
    }
    setAskLoading(false);
  };

  const handleSituationRoom = async () => {
    if (situationRoomLoading) return;
    setSituationRoomLoading(true);
    try { setSituationRoom(await getSituationRoom(selectedState)); } catch { /* */ }
    setSituationRoomLoading(false);
  };

  const selectState = useCallback(async (state: string | null) => {
    setSelectedState(state);
    setBriefing(null);
    setSituationRoom(null);
    getRegionalAnalytics(state).then(setRegionalAnalytics).catch(() => {});
    getDomainRadar(state).then(setDomainRadar).catch(() => {});
    getNarrativeConflicts(state).then(setConflicts).catch(() => {});
    if (state) {
      setBriefingLoading(true);
      try { setBriefing(await getAIBriefing(state)); } catch { /* */ }
      setBriefingLoading(false);
    }
  }, []);

  const resolveKey = (geo: any): string | null => {
    const n = geo.properties?.ST_NM || geo.properties?.state || geo.properties?.NAME_1 || geo.properties?.name || "";
    return STATE_NAME_MAP[n] || null;
  };

  const tooltipInfo = useMemo((): (Record<string, any> & { articleCount: number; avgSentiment: number }) | null => {
    if (!hoveredState) return null;
    const sd: Record<string, any> = stateData[hoveredState] || {};
    const hd = heatmapMap[hoveredState];
    return { ...sd, articleCount: hd?.article_count || 0, avgSentiment: hd?.avg_sentiment || 0 };
  }, [hoveredState, stateData, heatmapMap]);

  const saveChannels = (ch: string[]) => { setEnabledChannels(ch); try { localStorage.setItem("narad_channels", JSON.stringify(ch)); } catch { /* */ } };
  const visibleChannels = NEWS_CHANNELS.filter(c => enabledChannels.includes(c.id));

  // Auto-reset active channel if the selected one was removed from visible list
  useEffect(() => {
    if (visibleChannels.length > 0 && !visibleChannels.find(c => c.id === activeChannel)) {
      setActiveChannel(visibleChannels[0].id);
    }
  }, [visibleChannels, activeChannel]);

  return (
    <div style={{ background: "var(--bg-deep)" }}>
      <Navbar onSearchOpen={() => {}} language="all" onLanguageChange={() => {}} />
      <div style={{ paddingTop: "56px" }}>

      {/* ── THREE-COLUMN grid ───────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "200px 1fr 360px", minHeight: "calc(100vh - 56px)", width: "100%" }}>

        {/* ═══ LEFT: Intelligence Layers ═══ */}
        <div style={{
          borderRight: "1px solid var(--border-subtle)",
          height: "calc(100vh - 56px)",
          position: "sticky",
          top: "56px",
          display: "flex",
          flexDirection: "column",
          background: "var(--bg-elevated)",
        }}>
            <div style={{
              padding: "0.3rem 0.5rem", fontFamily: "var(--font-mono)", fontSize: "0.45rem",
              letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text-dim)",
              borderBottom: "1px solid var(--border-subtle)", background: "var(--bg-surface)",
              flexShrink: 0,
            }}>Regional Focus</div>
            <div style={{ overflowY: "auto", height: "30vh", borderBottom: "1px solid var(--border-subtle)", flexShrink: 0 }}>
              <button onClick={() => selectState(null)} style={{
                display: "flex", width: "100%", padding: "0.22rem 0.5rem", border: "none", cursor: "pointer",
                alignItems: "center", gap: "0.3rem",
                fontFamily: "var(--font-body)", fontSize: "0.65rem",
                background: !selectedState ? "var(--accent-dim)" : "transparent",
                color: !selectedState ? "var(--accent)" : "var(--text-secondary)",
                fontWeight: !selectedState ? 600 : 400,
              }}>🇮🇳 All India</button>
              {ALL_STATES.map(s => {
                const h = heatmapMap[s];
                const sel = selectedState === s;
                const hov = hoveredState === s;
                return (
                  <button key={s} onClick={() => { selectState(s); setShowStateOverlay(true); }}
                    onMouseEnter={() => setHoveredState(s)}
                    onMouseLeave={() => setHoveredState(null)}
                    style={{
                      display: "flex", width: "100%", padding: "0.18rem 0.5rem", border: "none", cursor: "pointer",
                      alignItems: "center", justifyContent: "space-between",
                      fontFamily: "var(--font-body)", fontSize: "0.62rem",
                      background: sel ? "var(--accent-dim)" : hov ? "#f5f5f5" : "transparent",
                      color: sel ? "var(--accent)" : "var(--text-secondary)",
                      fontWeight: sel ? 600 : 400, transition: "background 0.1s",
                    }}>
                    <span style={{ display: "flex", alignItems: "center", gap: "0.25rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {h && <span style={{ width: "4px", height: "4px", borderRadius: "50%", background: sentimentColor(h.avg_sentiment), flexShrink: 0, display: "inline-block" }} />}
                      {STATE_DISPLAY[s]}
                    </span>
                    {h && <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.45rem", color: "var(--text-dim)", flexShrink: 0 }}>{h.article_count}</span>}
                  </button>
                );
              })}
            </div>

            {/* Map Overlays Section */}
            <div style={{
              padding: "0.3rem 0.5rem", fontFamily: "var(--font-mono)", fontSize: "0.45rem",
              letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text-dim)",
              borderBottom: "1px solid var(--border-subtle)", background: "var(--bg-surface)",
              flexShrink: 0, marginTop: 0
            }}>Map Overlays</div>
            <div style={{ padding: "0.4rem", display: "flex", flexDirection: "column", gap: "0.4rem", flexShrink: 0, borderBottom: "1px solid var(--border-subtle)", flex: 1, overflowY: "auto" }}>
              <div style={{ fontFamily: "var(--font-body)", fontSize: "0.55rem", color: "var(--text-muted)", marginBottom: "0.2rem", lineHeight: 1.4 }}>
                Toggle tactical overlays to examine India's strategic assets on the map.
              </div>
              {[
                { id: "space_center", label: "Space Centers (ISRO)", icon: "🚀" },
                { id: "research_station", label: "Research Stations (DRDO/BARC)", icon: "🔬" },
                { id: "tourism", label: "Tourism Sector", icon: "🏛️" },
                { id: "borders", label: "State Borders", icon: "🗺️" },
              ].map(overlay => (
                <button
                  key={overlay.id}
                  onClick={() => toggleOverlay(overlay.id)}
                  style={{
                    display: "flex", alignItems: "center", gap: "0.4rem", padding: "0.45rem 0.5rem",
                    border: "1px solid",
                    borderColor: activeOverlays.has(overlay.id) ? "var(--accent)" : "var(--border-subtle)",
                    background: activeOverlays.has(overlay.id) ? "var(--bg-deep)" : "var(--bg-surface)",
                    color: activeOverlays.has(overlay.id) ? "var(--text-primary)" : "var(--text-secondary)",
                    fontFamily: "var(--font-body)", fontSize: "0.65rem", borderRadius: "6px",
                    cursor: "pointer", transition: "all 0.15s", fontWeight: activeOverlays.has(overlay.id) ? 600 : 400,
                    boxShadow: activeOverlays.has(overlay.id) ? "0 2px 8px rgba(0,0,0,0.05)" : "none"
                  }}
                >
                  <span style={{ fontSize: "0.8rem", width: "20px", textAlign: "center", borderRight: "1px solid var(--border-subtle)", paddingRight: "0.3rem" }}>{overlay.icon}</span>
                  <span style={{ flex: 1, textAlign: "left" }}>{overlay.label}</span>
                  <div style={{ 
                    width: "28px", height: "14px", borderRadius: "10px", 
                    background: activeOverlays.has(overlay.id) ? "var(--accent)" : "var(--border-subtle)",
                    position: "relative", transition: "background 0.2s"
                  }}>
                    <div style={{
                      width: "10px", height: "10px", borderRadius: "50%", background: "#fff",
                      position: "absolute", top: "2px", left: activeOverlays.has(overlay.id) ? "16px" : "2px",
                      transition: "left 0.2s"
                    }} />
                  </div>
                </button>
              ))}
            </div>
        </div>

        {/* ═══ CENTER: Map + News + Analytics ═══ */}
        <main style={{ overflowY: "auto", width: "100%", minWidth: 0, position: "relative" }}>

          {/* ── MAP (compact ~45vh) ────────────────────── */}
          <div style={{ position: "relative", background: "var(--bg-deep)", borderBottom: "1px solid var(--border-subtle)" }}
            onMouseMove={(e) => setTooltipPos({ x: e.clientX, y: e.clientY })}
          >
            {selectedState && !showStateOverlay && (
              <div style={{
                position: "absolute", top: "6px", left: "8px", zIndex: 10,
                padding: "0.2rem 0.4rem", background: "rgba(255,255,255,0.92)",
                border: "1px solid var(--border-subtle)", backdropFilter: "blur(6px)",
              }}>
                <span style={{ fontFamily: "var(--font-headline)", fontSize: "0.7rem", fontWeight: 700 }}>{STATE_DISPLAY[selectedState]}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.4rem", marginLeft: "0.3rem", color: "var(--accent)" }}>SELECTED</span>
              </div>
            )}

            <ComposableMap
              projection="geoMercator"
              projectionConfig={{ center: [82, 22], scale: 900 }}
              style={{ width: "100%", height: "45vh", display: "block" }}
            >
              <ZoomableGroup>
                {/* World Map Background (Context) */}
                <Geographies geography={"https://unpkg.com/world-atlas@2.0.2/countries-110m.json"}>
                  {({ geographies }) => geographies.map(geo => (
                    <Geography 
                      key={geo.rsmKey} 
                      geography={geo} 
                      style={{
                        default: { fill: "var(--bg-surface)", stroke: "var(--border-visible)", strokeWidth: 0.3, outline: "none" },
                        hover: { fill: "var(--bg-surface)", stroke: "var(--border-visible)", strokeWidth: 0.3, outline: "none" },
                        pressed: { fill: "var(--bg-surface)", stroke: "var(--border-visible)", strokeWidth: 0.3, outline: "none" }
                      }} 
                    />
                  ))}
                </Geographies>

                {/* India Map (Focus) */}
                <Geographies geography={INDIA_GEO}>
                  {({ geographies }) => geographies.map(geo => {
                    const k = resolveKey(geo);
                    const h = k ? heatmapMap[k] : null;
                    const sel = selectedState === k;
                    return (
                      <Geography key={geo.rsmKey} geography={geo}
                        onMouseEnter={() => k && setHoveredState(k)}
                        onMouseLeave={() => setHoveredState(null)}
                        onClick={() => {
                          if (k) {
                            selectState(k);
                            setShowStateOverlay(true);
                          }
                        }}
                        style={{
                          default: {
                            fill: sel ? "rgba(98, 141, 211, 0.2)" : h ? heatFill(h.avg_sentiment, h.article_count) : "var(--bg-surface)",
                            stroke: sel ? "var(--accent)" : "#888", strokeWidth: sel ? 1.5 : 0.8,
                            outline: "none", cursor: "pointer", transition: "fill 0.15s",
                          },
                          hover: { fill: sel ? "rgba(98, 141, 211, 0.3)" : "rgba(250, 179, 59, 0.3)", stroke: "var(--accent)", strokeWidth: 1.2, outline: "none", cursor: "pointer" },
                          pressed: { fill: "rgba(98, 141, 211, 0.4)", stroke: "var(--accent)", strokeWidth: 1.5, outline: "none" },
                        }}
                      />
                    );
                  })}
                </Geographies>

                {/* Overlays */}
                {Array.from(activeOverlays).map(type => 
                  mapMarkers[type]?.map(m => (
                    <Marker key={m.id} coordinates={m.coordinates}>
                      <circle r={2.5} fill={type === "space_center" ? "var(--accent)" : type === "research_station" ? "#FAB33B" : "#DDA5A1"} stroke="#fff" strokeWidth={0.5} style={{ filter: "drop-shadow(0px 0px 2px rgba(0,0,0,0.5))" }} />
                      <text
                        textAnchor="middle"
                        y={-10}
                        style={{ fontFamily: "var(--font-mono)", fontSize: "9px", fill: "var(--text-primary)", pointerEvents: "none", textShadow: "0 1px 3px rgba(255,255,255,1)", fontWeight: 700 }}
                      >
                        {m.name}
                      </text>
                    </Marker>
                  ))
                )}


              </ZoomableGroup>
            </ComposableMap>

            {/* Legend */}
            <div style={{
              position: "absolute", bottom: "10px", right: "20px", left:"auto",
              display: "flex", gap: "0.5rem", alignItems: "center",
              fontFamily: "var(--font-mono)", fontSize: "0.5rem", color: "var(--text-dim)",
              background: "rgba(255,255,255,0.8)", padding: "0.3rem 0.6rem", borderRadius: "4px", border: "1px solid var(--border-subtle)"
            }}>
              {[{ c: "#DDA5A1", l: "Neg" }, { c: "rgba(202, 128, 118, 0.5)", l: "-ve" }, { c: "var(--bg-surface)", l: "Neut" }, { c: "rgba(98, 141, 211, 0.5)", l: "+ve" }, { c: "#628DD3", l: "Pos" }].map((x, i) => (
                <span key={i} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <span style={{ width: "8px", height: "8px", background: x.c, border: "1px solid var(--border-visible)", display: "inline-block" }} />{x.l}
                </span>
              ))}
            </div>
          </div>

          {/* ── LIVE NEWS + ASK NARAD (side-by-side) ──────────── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", borderBottom: "1px solid var(--border-subtle)", height: "360px", overflow: "hidden" }}>

            {/* ── LEFT: Live News ───────── */}
            <div style={{ borderRight: "1px solid var(--border-subtle)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
              {/* Header */}
              <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "0.3rem 0.6rem", borderBottom: "1px solid var(--border-subtle)",
                background: "var(--bg-surface)", flexShrink: 0,
              }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.55rem", fontWeight: 700, letterSpacing: "0.08em", color: "var(--text-primary)" }}>LIVE NEWS</span>
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.45rem", color: "var(--accent)", display: "flex", alignItems: "center", gap: "0.2rem" }}>
                    <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: "var(--accent)", display: "inline-block" }} />LIVE
                  </span>
                  <button onClick={() => setChannelModalOpen(true)} style={{
                    background: "none", border: "1px solid var(--border-subtle)", cursor: "pointer", padding: "0.12rem 0.2rem",
                    fontFamily: "var(--font-mono)", fontSize: "0.4rem", color: "var(--text-muted)", borderRadius: "2px",
                  }}>⚙</button>
                </div>
              </div>
              {/* Channel tabs */}
              <div style={{ display: "flex", overflowX: "auto", borderBottom: "1px solid var(--border-subtle)", flexShrink: 0 }}>
                {visibleChannels.map(ch => (
                  <button key={ch.id} onClick={() => setActiveChannel(ch.id)} style={{
                    padding: "0.22rem 0.5rem", border: "none", cursor: "pointer",
                    fontFamily: "var(--font-mono)", fontSize: "0.45rem", fontWeight: 600, letterSpacing: "0.06em",
                    background: activeChannel === ch.id ? "var(--accent)" : "transparent",
                    color: activeChannel === ch.id ? "#fff" : "var(--text-muted)",
                    transition: "background 0.15s", whiteSpace: "nowrap",
                  }}>{ch.name}</button>
                ))}
              </div>
              {/* Player */}
              <div style={{ flex: 1, position: "relative", minHeight: "200px" }}>
                {visibleChannels.length > 0 ? (
                  <iframe key={activeChannel}
                    src={visibleChannels.find(c => c.id === activeChannel)?.embed || undefined}
                    style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", border: "none" }}
                    allow="autoplay; encrypted-media" allowFullScreen
                  />
                ) : (
                  <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-dim)", fontFamily: "var(--font-mono)", fontSize: "0.6rem" }}>
                    No channels enabled
                  </div>
                )}
              </div>
            </div>

            {/* ── RIGHT: Ask Narad ─────── */}
            <div style={{ display: "flex", flexDirection: "column", background: "var(--bg-elevated)", overflow: "hidden" }}>
              {/* Header */}
              <div style={{
                display: "flex", alignItems: "center", gap: "0.4rem",
                padding: "0.3rem 0.6rem", borderBottom: "1px solid var(--border-subtle)",
                background: "var(--bg-surface)", flexShrink: 0,
              }}>
                <span style={{ fontSize: "0.8rem" }}>💬</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-primary)" }}>Ask Narad</span>
              </div>

              {/* Chat history — scrollable */}
              <div style={{ flex: 1, overflowY: "auto", padding: "0.5rem", display: "flex", flexDirection: "column", gap: "0.45rem", minHeight: 0 }}>
                {askHistory.length === 0 && (
                  <div style={{ padding: "0.5rem", background: "var(--bg-deep)", border: "1px solid var(--border-subtle)" }}>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.42rem", color: "var(--text-dim)", marginBottom: "0.35rem" }}>Try asking:</div>
                    {["What is happening in Kashmir?", "Latest India economy news?", "Key political events this week?"].map((q, i) => (
                      <button key={i} onClick={() => { setAskQuestion(q); setTimeout(() => { setAskQuestion(""); setAskLoading(true); askNarad(q, selectedState).then(r => setAskHistory(prev => [...prev, { q, r }])).catch(() => setAskHistory(prev => [...prev, { q, r: { answer: "Failed to get answer. Please try again.", sources: [], pages_retrieved: 0, articles_scanned: 0, source: "error" } }])).finally(() => setAskLoading(false)); }, 0); }}
                        style={{ display: "block", width: "100%", textAlign: "left", padding: "0.25rem 0.4rem", margin: "0.12rem 0", background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", color: "var(--text-secondary)", fontFamily: "var(--font-body)", fontSize: "0.62rem", cursor: "pointer" }}>
                        {q}
                      </button>
                    ))}
                  </div>
                )}
                {askHistory.map((item, i) => (
                  <div key={i} style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                    {/* User bubble */}
                    <div style={{ display: "flex", justifyContent: "flex-end" }}>
                      <div style={{ maxWidth: "88%", padding: "0.4rem 0.55rem", background: "var(--accent)", color: "#fff", fontFamily: "var(--font-body)", fontSize: "0.65rem", lineHeight: 1.4 }}>
                        {item.q}
                      </div>
                    </div>
                    {/* Answer */}
                    <div style={{ padding: "0.45rem 0.55rem", background: "var(--bg-deep)", border: "1px solid var(--border-subtle)", fontFamily: "var(--font-body)", fontSize: "0.65rem", lineHeight: 1.6, color: "var(--text-primary)", whiteSpace: "pre-wrap" }}>
                      {i === askHistory.length - 1 ? (
                        <TypingEffect text={item.r.answer} speed={6} />
                      ) : (
                        item.r.answer
                      )}
                    </div>
                    {/* Sources */}
                    {item.r.sources.length > 0 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.15rem" }}>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.35rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                          {item.r.articles_scanned} articles · {item.r.pages_retrieved} pages
                        </div>
                        {item.r.sources.slice(0, 3).map((s: AskNaradSource, si: number) => (
                          <a key={si} href={s.url || "#"} target="_blank" rel="noreferrer"
                            style={{ display: "block", padding: "0.25rem 0.4rem", background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", textDecoration: "none" }}>
                            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.37rem", color: "var(--accent)", fontWeight: 600 }}>{s.source} · {Math.round(s.relevance_score * 100)}%</div>
                            <div style={{ fontFamily: "var(--font-body)", fontSize: "0.58rem", color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.title}</div>
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {askLoading && (
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", color: "var(--text-dim)", padding: "0.3rem" }}>⟳ Narad is thinking...</div>
                )}
                <div ref={askEndRef} />
              </div>

              {/* Input row */}
              <div style={{ display: "flex", gap: "0", borderTop: "1px solid var(--border-subtle)", flexShrink: 0 }}>
                <input
                  type="text" value={askQuestion}
                  onChange={e => setAskQuestion(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAskNarad(); } }}
                  placeholder="Ask anything about India..."
                  style={{
                    flex: 1, padding: "0.45rem 0.55rem",
                    background: "var(--bg-deep)", border: "none", borderRight: "1px solid var(--border-subtle)",
                    fontFamily: "var(--font-body)", fontSize: "0.68rem", color: "var(--text-primary)",
                    outline: "none",
                  }}
                />
                <button onClick={handleAskNarad} disabled={askLoading || !askQuestion.trim()}
                  style={{
                    padding: "0.45rem 0.75rem", background: askLoading ? "var(--bg-surface)" : "var(--accent)",
                    color: askLoading ? "var(--text-dim)" : "#fff", border: "none",
                    cursor: askLoading ? "not-allowed" : "pointer",
                    fontFamily: "var(--font-mono)", fontSize: "0.6rem", transition: "background 0.15s", flexShrink: 0,
                  }}>
                  {askLoading ? "…" : "→"}
                </button>
              </div>
            </div>

          </div>

          {/* ── ECONOMIC ANALYTICS (3-col grid below news) ──────────── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0", borderBottom: "1px solid var(--border-subtle)" }}>

            {/* ── COL 1: Rupee Analytics ── */}
            <div style={{ borderRight: "1px solid var(--border-subtle)", padding: "0.8rem", background: "var(--bg-elevated)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", marginBottom: "0.6rem" }}>
                <span style={{ fontSize: "0.8rem" }}>💱</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-primary)", fontWeight: 700 }}>Rupee Analytics</span>
                <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: "0.35rem", color: "var(--text-dim)" }}>LIVE</span>
              </div>
              {!markets ? (
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", color: "var(--text-muted)", padding: "1rem 0", textAlign: "center" }}>Loading...</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
                    <span style={{ fontFamily: "var(--font-headline)", fontSize: "1.6rem", fontWeight: 700, color: "var(--text-primary)" }}>₹{(markets.rupee_usd || 83.50).toFixed(2)}</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.45rem", color: "var(--text-dim)" }}>/ 1 USD</span>
                  </div>
                  {/* Gauge bar */}
                  <div style={{ marginTop: "0.3rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "var(--font-mono)", fontSize: "0.35rem", color: "var(--text-dim)", marginBottom: "0.2rem" }}>
                      <span>80.00</span><span>85.00</span><span>90.00</span>
                    </div>
                    <div style={{ height: "6px", background: "rgba(0,0,0,0.06)", borderRadius: "3px", position: "relative", overflow: "hidden" }}>
                      <div style={{ width: `${Math.min(100, Math.max(0, (((markets.rupee_usd || 83.50) - 80) / 10) * 100))}%`, height: "100%", background: "linear-gradient(90deg, #628DD3, #FAB33B, #CA8076)", borderRadius: "3px", transition: "width 0.5s" }} />
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.4rem", marginTop: "0.3rem" }}>
                    <div style={{ padding: "0.3rem 0.4rem", background: "var(--bg-deep)", border: "1px solid var(--border-subtle)", borderRadius: "4px" }}>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.35rem", color: "var(--text-dim)", textTransform: "uppercase" }}>EUR/INR</div>
                      <div style={{ fontFamily: "var(--font-headline)", fontSize: "0.7rem", fontWeight: 600, color: "var(--text-primary)" }}>₹{(markets.eur_inr || 90.45).toFixed(2)}</div>
                    </div>
                    <div style={{ padding: "0.3rem 0.4rem", background: "var(--bg-deep)", border: "1px solid var(--border-subtle)", borderRadius: "4px" }}>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.35rem", color: "var(--text-dim)", textTransform: "uppercase" }}>GBP/INR</div>
                      <div style={{ fontFamily: "var(--font-headline)", fontSize: "0.7rem", fontWeight: 600, color: "var(--text-primary)" }}>₹{(markets.gbp_inr || 105.20).toFixed(2)}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* ── COL 2: Resource Analytics ── */}
            <div style={{ borderRight: "1px solid var(--border-subtle)", padding: "0.8rem", background: "var(--bg-elevated)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", marginBottom: "0.6rem" }}>
                <span style={{ fontSize: "0.8rem" }}>⛽</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-primary)", fontWeight: 700 }}>Resource Analytics</span>
                <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: "0.35rem", color: "var(--text-dim)" }}>INR</span>
              </div>
              {!markets ? (
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", color: "var(--text-muted)", padding: "1rem 0", textAlign: "center" }}>Loading...</div>
              ) : (() => {
                const inr = markets.rupee_usd || 83;
                const pctChg = (cur: number | null, prev: number | null) => {
                  if (!cur || !prev || prev === 0) return null;
                  return ((cur - prev) / prev) * 100;
                };
                const resources = [
                  { name: "Crude Oil", icon: "🛢️", usd: markets.crude_oil, prev: markets.crude_oil_prev, unit: "/bbl", color: "#628DD3" },
                  { name: "Gold", icon: "🥇", usd: markets.gold, prev: markets.gold_prev, unit: "/oz", color: "#FAB33B" },
                  { name: "Silver", icon: "🪙", usd: markets.silver, prev: markets.silver_prev, unit: "/oz", color: "#9CA3AF" },
                  { name: "Natural Gas", icon: "🔥", usd: markets.natural_gas, prev: markets.natural_gas_prev, unit: "/MMBtu", color: "#DDA5A1" },
                ];
                return (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                    {resources.map((r, i) => {
                      const chg = pctChg(r.usd, r.prev);
                      const chgColor = chg !== null ? (chg >= 0 ? "#22c55e" : "#ef4444") : "var(--text-dim)";
                      return (
                        <div key={i} style={{ padding: "0.35rem 0.5rem", background: "var(--bg-deep)", border: "1px solid var(--border-subtle)", borderRadius: "5px", borderLeft: `3px solid ${r.color}` }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.15rem" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                              <span style={{ fontSize: "0.65rem" }}>{r.icon}</span>
                              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.38rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{r.name}</span>
                            </div>
                            {chg !== null && <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.32rem", color: chgColor, background: `${chgColor}15`, padding: "0.1rem 0.2rem", borderRadius: "8px" }}>{chg >= 0 ? "+" : ""}{chg.toFixed(2)}%</span>}
                          </div>
                          <div style={{ display: "flex", alignItems: "baseline", gap: "0.3rem" }}>
                            <span style={{ fontFamily: "var(--font-headline)", fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }}>₹{r.usd ? (r.usd * inr).toLocaleString("en-IN", { maximumFractionDigits: 0 }) : "---"}</span>
                            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.35rem", color: r.color }}>{r.unit}</span>
                            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.32rem", color: "var(--text-dim)", marginLeft: "auto" }}>${r.usd ? r.usd.toFixed(2) : "---"}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}
            </div>

            {/* ── COL 3: Market Analytics ── */}
            <div style={{ padding: "0.8rem", background: "var(--bg-elevated)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", marginBottom: "0.6rem" }}>
                <span style={{ fontSize: "0.8rem" }}>📈</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-primary)", fontWeight: 700 }}>Market Analytics</span>
              </div>
              {!markets ? (
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", color: "var(--text-muted)", padding: "1rem 0", textAlign: "center" }}>Loading...</div>
              ) : (() => {
                const pctChg = (cur: number | null, prev: number | null) => {
                  if (!cur || !prev || prev === 0) return null;
                  return ((cur - prev) / prev) * 100;
                };
                const indices = [
                  { name: "NIFTY 50", val: markets.nifty, prev: markets.nifty_prev },
                  { name: "BSE SENSEX", val: markets.sensex, prev: markets.sensex_prev },
                ];
                return (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                    {indices.map((idx, i) => {
                      const chg = pctChg(idx.val, idx.prev);
                      const chgColor = chg !== null ? (chg >= 0 ? "#22c55e" : "#ef4444") : "#628DD3";
                      return (
                        <div key={i} style={{ padding: "0.5rem 0.6rem", background: "var(--bg-deep)", border: "1px solid var(--border-subtle)", borderRadius: "6px", boxShadow: "0 2px 4px rgba(0,0,0,0.02)" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.3rem" }}>
                            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.42rem", fontWeight: 600, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{idx.name}</span>
                            {chg !== null && <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.35rem", color: chgColor, background: `${chgColor}15`, padding: "0.12rem 0.25rem", borderRadius: "10px" }}>{chg >= 0 ? "+" : ""}{chg.toFixed(2)}%</span>}
                          </div>
                          <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
                            <span style={{ fontFamily: "var(--font-headline)", fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)" }}>{idx.val ? idx.val.toLocaleString('en-IN') : "---"}</span>
                            {idx.prev && idx.val && <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.35rem", color: "var(--text-dim)" }}>prev: {idx.prev.toLocaleString('en-IN')}</span>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}
            </div>

          </div>


          {/* ── TOOLTIP ────────────────────────────────── */}
          <AnimatePresence>
            {hoveredState && tooltipInfo && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.08 }}
                style={{
                  position: "fixed", left: tooltipPos.x + 14, top: tooltipPos.y - 10, zIndex: 100,
                  background: "#fff", border: "1px solid var(--border-subtle)",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.1)", padding: "0.45rem 0.5rem",
                  minWidth: "180px", maxWidth: "240px", pointerEvents: "none",
                }}>
                <div style={{ fontFamily: "var(--font-headline)", fontSize: "0.72rem", fontWeight: 700, color: "var(--text-primary)" }}>{STATE_DISPLAY[hoveredState]}</div>
                {tooltipInfo.capital && <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.4rem", color: "var(--text-muted)", marginBottom: "0.2rem" }}>Capital: {tooltipInfo.capital}</div>}
                <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "0.2rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.15rem 0.4rem" }}>
                  {[{ l: "Population", v: tooltipInfo.population }, { l: "Literacy", v: tooltipInfo.literacy }, { l: "Crime Rate", v: tooltipInfo.crime_rate }, { l: "GDP/Cap", v: tooltipInfo.gdp_per_capita }]
                    .filter(x => x.v).map((r, i) => (
                      <div key={i}>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.35rem", letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--text-dim)" }}>{r.l}</div>
                        <div style={{ fontFamily: "var(--font-headline)", fontSize: "0.58rem", fontWeight: 600, color: "var(--text-primary)" }}>{r.v}</div>
                      </div>
                    ))}
                </div>
                <div style={{ borderTop: "1px solid var(--border-subtle)", marginTop: "0.2rem", paddingTop: "0.15rem", display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.38rem", color: "var(--text-muted)" }}>📰 {tooltipInfo.articleCount}</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.38rem", fontWeight: 600, color: sentimentColor(tooltipInfo.avgSentiment) }}>● {sentimentLabel(tooltipInfo.avgSentiment)}</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>



        </main>

        {/* ═══ RIGHT: GenAI Command Center ═════ */}
        <div style={{
          borderLeft: "1px solid var(--border-subtle)",
          height: "calc(100vh - 56px)",
          position: "sticky",
          top: "56px",
          background: "var(--bg-deep)",
          zIndex: 5,
        }}>
          {/* Scrollable Command Center */}
          <div style={{ overflowY: "auto", overflowX: "hidden", height: "100%", display: "flex", flexDirection: "column", gap: 0, padding: "0.75rem" }}>
            {/* ── Panel header ── */}
            <div style={{
              padding: "0.5rem 0.6rem", borderBottom: "2px solid var(--accent)",
              fontFamily: "var(--font-mono)", fontSize: "0.46rem", letterSpacing: "0.12em",
              textTransform: "uppercase", color: "var(--accent)", fontWeight: 700,
              background: "var(--bg-surface)", marginBottom: "0.6rem",
              display: "flex", alignItems: "center", gap: "0.35rem", flexShrink: 0,
            }}>
              <span>⚡</span> GenAI Command Center
              {selectedState && <span style={{ color: "var(--text-dim)", fontWeight: 400 }}>· {STATE_DISPLAY[selectedState] ?? selectedState}</span>}
            </div>

            {/* ─── BOX 1: Regional Analytics ─────────────────── */}
            <div style={{
              border: "1px solid var(--border-subtle)", background: "var(--bg-elevated)",
              marginBottom: "0.5rem", overflow: "hidden", minHeight: "270px",
            }}>
            <div style={{
              padding: "0.45rem 0.75rem", background: "var(--bg-surface)",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex", alignItems: "center", gap: "0.4rem",
            }}>
              <span style={{ fontSize: "0.85rem" }}>📊</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.48rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-primary)", fontWeight: 700 }}>Regional Analytics</span>
            </div>
            <div style={{ padding: "0.75rem" }}>
              {!regionalAnalytics ? (
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.55rem", color: "var(--text-muted)", textAlign: "center", padding: "1rem 0" }}>Loading...</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                  {/* Technology */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.4rem" }}>
                    <div style={{ padding: "0.5rem 0.6rem", background: "var(--bg-deep)", border: "1px solid var(--border-subtle)", borderLeft: "3px solid #628DD3" }}>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.42rem", color: "var(--text-dim)", marginBottom: "0.15rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>AI Growth</div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontFamily: "var(--font-headline)", fontSize: "0.95rem", fontWeight: 700, color: "#628DD3" }}>{regionalAnalytics.tech.ai_growth}</span>
                        <Sparkline data={regionalAnalytics.tech.sparkline} color="#628DD3" w={38} h={14} />
                      </div>
                    </div>
                    <div style={{ padding: "0.5rem 0.6rem", background: "var(--bg-deep)", border: "1px solid var(--border-subtle)", borderLeft: "3px solid #628DD3" }}>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.42rem", color: "var(--text-dim)", marginBottom: "0.15rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>Est. Activity</div>
                      <span style={{ fontFamily: "var(--font-headline)", fontSize: "0.95rem", fontWeight: 700, color: "var(--text-primary)" }}>{regionalAnalytics.tech.funding}</span>
                    </div>
                  </div>
                  {/* Political */}
                  <div style={{ padding: "0.5rem 0.6rem", background: "var(--bg-deep)", border: "1px solid var(--border-subtle)", borderLeft: "3px solid #FAB33B" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.3rem" }}>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.42rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Public Sentiment</span>
                      <span style={{ fontFamily: "var(--font-headline)", fontSize: "0.85rem", fontWeight: 700 }}>{regionalAnalytics.political.sentiment_index}</span>
                    </div>
                    <div style={{ height: "5px", background: "var(--bg-surface)", borderRadius: "3px", overflow: "hidden" }}>
                      <div style={{ width: `${regionalAnalytics.political.sentiment_value}%`, height: "100%", background: regionalAnalytics.political.sentiment_value > 70 ? "#628DD3" : regionalAnalytics.political.sentiment_value > 40 ? "#FAB33B" : "#CA8076", transition: "width 0.4s" }} />
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.2rem", marginTop: "0.35rem" }}>
                      {regionalAnalytics.political.top_policies.map((tag, i) => (
                        <span key={i} style={{ padding: "0.12rem 0.3rem", background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", fontFamily: "var(--font-mono)", fontSize: "0.38rem", color: "var(--text-secondary)" }}>{tag}</span>
                      ))}
                    </div>
                  </div>
                  {/* Societal */}
                  <div style={{ padding: "0.5rem 0.6rem", background: "var(--bg-deep)", border: "1px solid var(--border-subtle)", borderLeft: "3px solid #DDA5A1" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.42rem", color: "var(--text-dim)", marginBottom: "0.1rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>Urban/Migration</div>
                        <span style={{ fontFamily: "var(--font-headline)", fontSize: "0.95rem", fontWeight: 700, color: "#DDA5A1" }}>{regionalAnalytics.societal.migration_rate}</span>
                      </div>
                      <Sparkline data={regionalAnalytics.societal.sparkline} color="#DDA5A1" w={38} h={14} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>


          {/* ─── BOX 2: Geo-Sentiment Radar ─────────────────── */}
          <div style={{
            border: "1px solid var(--border-subtle)", background: "var(--bg-elevated)",
            marginBottom: "0.5rem", overflow: "hidden", minHeight: "250px",
          }}>
            <div style={{
              padding: "0.4rem 0.65rem", background: "var(--bg-surface)",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex", alignItems: "center", gap: "0.4rem",
            }}>
              <span style={{ fontSize: "0.8rem" }}>🌐</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.46rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-primary)", fontWeight: 700 }}>Geo-Sentiment Radar</span>
              <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: "0.33rem", color: "var(--text-dim)" }}>$0 · live</span>
            </div>
            <div style={{ padding: "0.6rem" }}>
              {!domainRadar ? (
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", color: "var(--text-muted)", padding: "0.5rem 0", textAlign: "center" }}>Loading radar...</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  <div style={{ display: "flex", justifyContent: "center" }}><DomainRadar domains={domainRadar.domains} /></div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                    {Object.entries(domainRadar.domains).map(([domain, data]) => {
                      const s = data.sentiment;
                      const pct = Math.round(((s + 1) / 2) * 100);
                      const col = s > 0.1 ? "#628DD3" : s < -0.1 ? "#CA8076" : "#FAB33B";
                      return (
                        <div key={domain} style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.38rem", color: "var(--text-secondary)", width: "58px", flexShrink: 0 }}>{domain}</span>
                          <div style={{ flex: 1, height: "3px", background: "var(--bg-deep)", borderRadius: "2px", overflow: "hidden" }}>
                            <div style={{ width: `${pct}%`, height: "100%", background: col, transition: "width 0.4s" }} />
                          </div>
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.38rem", color: col, fontWeight: 600, minWidth: "30px", textAlign: "right" }}>{s >= 0 ? "+" : ""}{s.toFixed(2)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ─── BOX 3: AI Situation Room ───────────────────── */}
          <div style={{
            border: "1px solid var(--border-subtle)", background: "var(--bg-elevated)",
            marginBottom: "0.5rem", overflow: "hidden", minHeight: "250px",
          }}>
            <div style={{
              padding: "0.45rem 0.75rem", background: "var(--bg-surface)",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex", alignItems: "center", gap: "0.4rem",
            }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.48rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-primary)", fontWeight: 700 }}>Narad Situation Room</span>
              <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: "0.35rem", color: "var(--text-dim)" }}>24h brief · Haiku</span>
            </div>
            <div style={{ padding: "0.75rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.44rem", color: "var(--text-dim)", margin: 0, lineHeight: 1.5 }}>
                Narad-generated intelligence digest for {selectedState ? (STATE_DISPLAY[selectedState] ?? selectedState) : "All India"}.
              </p>
              {!situationRoom ? (
                <button onClick={handleSituationRoom} disabled={situationRoomLoading}
                  style={{
                    padding: "0.55rem 1rem", background: situationRoomLoading ? "var(--bg-deep)" : "var(--accent)",
                    color: situationRoomLoading ? "var(--text-dim)" : "#fff", border: "none",
                    fontFamily: "var(--font-mono)", fontSize: "0.48rem", letterSpacing: "0.1em",
                    textTransform: "uppercase", cursor: situationRoomLoading ? "not-allowed" : "pointer",
                    transition: "all 0.2s", display: "flex", alignItems: "center", justifyContent: "center", gap: "0.4rem",
                  }}>
                  {situationRoomLoading ? "⟳ Generating..." : "⚡ Generate Intel Brief"}
                </button>
              ) : (
                <div>
                  <div style={{
                    padding: "0.65rem 0.75rem", background: "var(--bg-deep)", border: "1px solid var(--border-subtle)",
                    fontFamily: "var(--font-body)", fontSize: "0.68rem", lineHeight: 1.65,
                    color: "var(--text-primary)", whiteSpace: "pre-wrap",
                  }}>
                    {situationRoom.briefing}
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: "0.35rem" }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.38rem", color: "var(--text-dim)" }}>{situationRoom.articles_used} articles · {situationRoom.source}</span>
                    <button onClick={() => setSituationRoom(null)} style={{ fontFamily: "var(--font-mono)", fontSize: "0.4rem", color: "var(--text-dim)", background: "none", border: "none", cursor: "pointer" }}>Refresh ↺</button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ─── BOX 4: Narrative Conflicts ─────────────────── */}
          <div style={{
            border: "1px solid var(--border-subtle)", background: "var(--bg-elevated)",
            marginBottom: "0.5rem", overflow: "hidden", minHeight: "300px",
          }}>
            <div style={{
              padding: "0.45rem 0.75rem", background: "var(--bg-surface)",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex", alignItems: "center", gap: "0.4rem",
            }}>
              <span style={{ fontSize: "0.85rem" }}>⚔️</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.48rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-primary)", fontWeight: 700 }}>Narrative Conflicts</span>
              {conflicts && <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: "0.38rem", color: conflicts.total > 0 ? "#CA8076" : "#628DD3", fontWeight: 600 }}>{conflicts.total} found</span>}
            </div>
            <div style={{ padding: "0.6rem", display: "flex", flexDirection: "column", gap: "0.5rem", maxHeight: "320px", overflowY: "auto" }}>
              {!conflicts ? (
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", color: "var(--text-muted)", padding: "0.5rem 0" }}>Loading...</div>
              ) : conflicts.conflicts.length === 0 ? (
                <div style={{ padding: "0.6rem", background: "var(--bg-deep)", border: "1px solid var(--border-subtle)", fontFamily: "var(--font-mono)", fontSize: "0.5rem", color: "#628DD3" }}>
                  ✅ No conflicts detected in last 48h.
                </div>
              ) : conflicts.conflicts.map((c, i) => (
                <div key={i} style={{ padding: "0.6rem", background: "var(--bg-deep)", border: "1px solid rgba(202, 128, 118, 0.25)", borderLeft: "3px solid #CA8076" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.3rem" }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.42rem", color: "#CA8076", fontWeight: 700 }}>CONFLICT</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.38rem", color: "var(--text-dim)" }}>Δ{c.sentiment_delta.toFixed(2)}</span>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.35rem", marginBottom: "0.35rem" }}>
                    <div style={{ padding: "0.3rem 0.4rem", background: "rgba(98, 141, 211, 0.08)", border: "1px solid rgba(98, 141, 211, 0.25)" }}>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.4rem", color: "#628DD3", fontWeight: 600 }}>{c.article_a.source}</div>
                      <div style={{ fontFamily: "var(--font-body)", fontSize: "0.58rem", color: "var(--text-primary)", lineHeight: 1.3, marginTop: "0.1rem" }}>{c.article_a.title.slice(0, 55)}…</div>
                    </div>
                    <div style={{ padding: "0.3rem 0.4rem", background: "rgba(202, 128, 118, 0.08)", border: "1px solid rgba(202, 128, 118, 0.25)" }}>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.4rem", color: "#CA8076", fontWeight: 600 }}>{c.article_b.source}</div>
                      <div style={{ fontFamily: "var(--font-body)", fontSize: "0.58rem", color: "var(--text-primary)", lineHeight: 1.3, marginTop: "0.1rem" }}>{c.article_b.title.slice(0, 55)}…</div>
                    </div>
                  </div>
                  <div style={{ fontFamily: "var(--font-body)", fontSize: "0.6rem", color: "var(--text-secondary)", lineHeight: 1.4, fontStyle: "italic" }}>{c.explanation}</div>
                </div>
              ))}
            </div>
          </div>
          </div> {/* end of Scrollable Command Center */}

        </div>
      </div>{/* end three-col grid */}
      </div>{/* end paddingTop */}

      {/* ── State Intelligence Overlay ─────────────────────── */}
      <AnimatePresence>
        {showStateOverlay && selectedState && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}
            style={{
              position: "fixed", top: "56px", left: 0, right: 0, bottom: 0,
              background: "rgba(255, 255, 255, 0.88)", backdropFilter: "blur(32px)", WebkitBackdropFilter: "blur(32px)",
              zIndex: 600, overflowY: "auto",
              padding: "2rem 3rem", display: "flex", flexDirection: "column",
            }}>
              {(() => {
                const hData = heatmapMap[selectedState];
                const sentiment = hData ? hData.avg_sentiment : 0;
                const instabilityScore = Math.round(((1 - sentiment) / 2) * 100);
                const instabilityText = instabilityScore > 70 ? "critical" : instabilityScore > 40 ? "watch" : "stable";
                const crimeStr = stateData[selectedState]?.crime_rate || "";
                const crimeVal = parseInt(crimeStr) || 200;
                const crimePct = Math.min(100, Math.max(10, (crimeVal / 800) * 100));
                const articleCount = hData ? hData.article_count : 0;
                const protestPct = Math.min(100, Math.max(5, (articleCount / 100) * 100));
                return (
                  <>
                    {/* Header */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.2rem", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.5rem" }}>
                      <div>
                        <div style={{ fontFamily: "var(--font-headline)", fontSize: "1.4rem", fontWeight: 700, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          {STATE_DISPLAY[selectedState]}
                        </div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.55rem", letterSpacing: "0.08em", color: "var(--text-dim)", textTransform: "uppercase", marginTop: "0.2rem" }}>
                          IN  •  Regional Intelligence
                        </div>
                      </div>
                      <button onClick={() => setShowStateOverlay(false)} style={{ background: "rgba(255,255,255,0.9)", border: "1px solid var(--border-subtle)", padding: "0.5rem 0.8rem", cursor: "pointer", fontFamily: "var(--font-mono)", fontSize: "0.6rem", color: "var(--text-secondary)", borderRadius: "6px", fontWeight: 600, boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}>
                        ✕ Close
                      </button>
                    </div>
                    {/* Top Scores */}
                    <div style={{ display: "flex", gap: "1.5rem", marginBottom: "1.5rem" }}>
                      <div style={{ flex: 1, background: "rgba(255,255,255,0.7)", padding: "1.2rem", borderRadius: "12px", border: "1px solid var(--border-subtle)", boxShadow: "0 4px 16px rgba(0,0,0,0.03)" }}>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.55rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "0.6rem" }}>Instability Index</div>
                        <div style={{ display: "flex", alignItems: "baseline", gap: "0.6rem" }}>
                          <span style={{ fontFamily: "var(--font-headline)", fontSize: "2.2rem", fontWeight: 700, color: instabilityScore > 70 ? "#CA8076" : instabilityScore > 40 ? "#FAB33B" : "var(--accent)" }}>{instabilityScore}<span style={{ fontSize: "1.2rem", color: "var(--text-dim)" }}>/100</span></span>
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-muted)" }}>→ {instabilityText}</span>
                        </div>
                      </div>
                      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: "0.8rem", background: "rgba(255,255,255,0.7)", padding: "1.2rem", borderRadius: "12px", border: "1px solid var(--border-subtle)", boxShadow: "0 4px 16px rgba(0,0,0,0.03)" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.8rem" }}>
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", color: "var(--text-secondary)", width: "60px", textTransform: "uppercase" }}>Crime</span>
                          <div style={{ flex: 1, height: "6px", background: "rgba(0,0,0,0.06)", borderRadius: "3px", overflow: "hidden" }}><div style={{ width: `${crimePct}%`, height: "100%", background: "#628DD3", borderRadius: "3px" }} /></div>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.8rem" }}>
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.5rem", color: "var(--text-secondary)", width: "60px", textTransform: "uppercase" }}>Protest</span>
                          <div style={{ flex: 1, height: "6px", background: "rgba(0,0,0,0.06)", borderRadius: "3px", overflow: "hidden" }}><div style={{ width: `${protestPct}%`, height: "100%", background: "#FAB33B", borderRadius: "3px" }} /></div>
                        </div>
                      </div>
                    </div>
                    {/* Active Signals */}
                    <div style={{ background: "rgba(255,255,255,0.7)", border: "1px solid var(--border-subtle)", borderRadius: "12px", padding: "1.2rem", marginBottom: "1.5rem", boxShadow: "0 4px 16px rgba(0,0,0,0.03)" }}>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.55rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-dim)", marginBottom: "0.8rem" }}>Active Signals</div>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
                        {[{ l: "Capital", k: "capital", i: "🏛" }, { l: "Population", k: "population", i: "👥" }, { l: "Literacy", k: "literacy", i: "📚" }, { l: "Crime Rate", k: "crime_rate", i: "🔒" }, { l: "GDP/Capita", k: "gdp_per_capita", i: "💰" }, { l: "Area", k: "area", i: "📐" }].map((f, idx) => {
                          const v = stateData[selectedState]?.[f.k];
                          if (!v) return null;
                          return (
                            <div key={idx} style={{ display: "flex", alignItems: "center", gap: "0.8rem", background: "rgba(255,255,255,0.85)", padding: "0.8rem 1rem", border: "1px solid var(--border-subtle)", borderRadius: "8px" }}>
                              <span style={{ fontSize: "1.2rem", width: "28px", textAlign: "center" }}>{f.i}</span>
                              <div>
                                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.45rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-dim)" }}>{f.l}</div>
                                <div style={{ fontFamily: "var(--font-headline)", fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)", marginTop: "0.15rem" }}>{v}</div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                    {/* Briefing */}
                    <div style={{ flex: 1, background: "rgba(255,255,255,0.7)", border: "1px solid var(--border-subtle)", borderRadius: "12px", padding: "1.2rem", boxShadow: "0 4px 16px rgba(0,0,0,0.03)", display: "flex", flexDirection: "column" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.8rem", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.6rem" }}>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.55rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-dim)" }}>Narad Intelligence Briefing</div>
                        {briefing?.source === "cache" && <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.45rem", color: "var(--text-muted)", background: "rgba(0,0,0,0.04)", padding: "0.3rem 0.5rem", borderRadius: "4px" }}>CACHED</span>}
                      </div>
                      {briefingLoading ? (
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-muted)", padding: "1rem" }}>Analyzing intelligence streams...</div>
                      ) : briefing ? (
                        <div style={{ fontFamily: "var(--font-body)", fontSize: "0.75rem", lineHeight: 1.75, color: "var(--text-primary)", whiteSpace: "pre-wrap", flex: 1, overflowY: "auto" }}>
                          <TypingEffect text={briefing.briefing} speed={5} />
                        </div>
                      ) : (
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-muted)", padding: "1rem" }}>No briefing data available.</div>
                      )}
                    </div>
                  </>
                );
              })()}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Channel Settings Modal ─────────────────────── */}
      <AnimatePresence>
        {channelModalOpen && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{ position: "fixed", inset: 0, zIndex: 200, background: "rgba(0,0,0,0.3)", display: "flex", alignItems: "center", justifyContent: "center" }}
            onClick={() => setChannelModalOpen(false)}>
            <motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }} onClick={e => e.stopPropagation()}
              style={{ background: "#fff", border: "1px solid var(--border-subtle)", padding: "0.8rem 1rem", minWidth: "280px", boxShadow: "0 12px 48px rgba(0,0,0,0.15)" }}>
              <div style={{ fontFamily: "var(--font-headline)", fontSize: "0.8rem", fontWeight: 700, marginBottom: "0.4rem" }}>News Channel Preferences</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.45rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>Select channels for live feed</div>
              {NEWS_CHANNELS.map(ch => (
                <label key={ch.id} style={{ display: "flex", alignItems: "center", gap: "0.35rem", padding: "0.2rem 0", cursor: "pointer", fontFamily: "var(--font-body)", fontSize: "0.7rem", color: "var(--text-primary)" }}>
                  <input type="checkbox" checked={enabledChannels.includes(ch.id)}
                    onChange={() => { const n = enabledChannels.includes(ch.id) ? enabledChannels.filter(c => c !== ch.id) : [...enabledChannels, ch.id]; saveChannels(n); }}
                    style={{ accentColor: "var(--accent)" }}
                  />{ch.name}
                </label>
              ))}
              <button onClick={() => setChannelModalOpen(false)} style={{
                marginTop: "0.5rem", width: "100%", padding: "0.35rem",
                border: "1px solid var(--accent)", background: "var(--accent-dim)", color: "var(--accent)",
                fontFamily: "var(--font-mono)", fontSize: "0.5rem", fontWeight: 600, cursor: "pointer",
              }}>Done</button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
      </div>
  );
}
