/**
 * Sentio Mind — Behaviour Intelligence Dashboard
 * Aligned with Brand Guidelines: #0F4C5C / #2EC4B6 / #6FBEDC / #F7F9FB / #3A3F45
 * Typography: Inter, Poppins, DM Sans
 * Style: Calm intelligence — trustworthy, non-intrusive, humane
 */

import { useState, useEffect } from "react";
import LogoutButton from "./components/LogoutButton";
import { useSession } from "./context/SessionContext";
import icon from "./assets/icon.png";
import { API_BASE } from "./config/env";
import { apiFetch } from "./utils/api";

// ─── Brand tokens (strict brand guideline compliance) ─────────────────────────
const BRAND = {
  deepTeal:    "#0F4C5C",
  aquaTeal:    "#2EC4B6",
  softBlue:    "#6FBEDC",
  offWhite:    "#F7F9FB",
  charcoal:    "#3A3F45",
  // Derived
  tealLight:   "rgba(46,196,182,0.12)",
  tealBorder:  "rgba(46,196,182,0.22)",
  tealBorder2: "rgba(46,196,182,0.35)",
  navBg:       "rgba(247,249,251,0.92)",
  darkBg:      "#0a1520",
  darkCard:    "rgba(255,255,255,0.04)",
  surface:     "#ffffff",
  borderLight: "rgba(58,63,69,0.1)",
  borderMid:   "rgba(58,63,69,0.15)",
  textPrimary: "#0F4C5C",
  textBody:    "#3A3F45",
  textMuted:   "#6b7b82",
  textFaint:   "#9eaeb3",
  green:       "#22c55e",
  amber:       "#f59e0b",
  red:         "#ef4444",
};

const GLOBAL_STYLE = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Poppins:wght@600;700;800&family=DM+Sans:wght@400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body { font-family: 'Inter', 'DM Sans', sans-serif; }

  @keyframes spin { to { transform: rotate(360deg); } }

  @keyframes scanLine {
    0%   { top: 6%;  opacity: 0.8; }
    48%  { top: 92%; opacity: 0.8; }
    50%  { top: 92%; opacity: 0; }
    52%  { top: 6%;  opacity: 0; }
    54%  { top: 6%;  opacity: 0.8; }
    100% { top: 6%;  opacity: 0.8; }
  }

  @keyframes glowPulse {
    0%,100% { box-shadow: 0 0 18px rgba(46,196,182,0.18), 0 0 40px rgba(15,76,92,0.08); }
    50%      { box-shadow: 0 0 32px rgba(46,196,182,0.32), 0 0 60px rgba(15,76,92,0.14); }
  }

  @keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position:  200% center; }
  }

  @keyframes barGrow {
    from { width: 0; }
    to   { width: var(--w); }
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  @keyframes liveDot {
    0%,100% { opacity: 1; }
    50%      { opacity: 0.25; }
  }

  .sentio-dash {
    font-family: 'Inter', 'DM Sans', sans-serif;
    background: ${BRAND.offWhite};
    color: ${BRAND.textBody};
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ── Scrollbar ── */
  .sentio-dash ::-webkit-scrollbar { width: 5px; }
  .sentio-dash ::-webkit-scrollbar-track { background: ${BRAND.offWhite}; }
  .sentio-dash ::-webkit-scrollbar-thumb { background: ${BRAND.aquaTeal}; border-radius: 4px; }

  /* ── Nav ── */
  .sd-nav {
    position: sticky; top: 0; z-index: 50;
    display: flex; align-items: center; justify-content: space-between;
    height: 95px; padding: 0 28px;
    background: ${BRAND.navBg};
    backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    border-bottom: 1px solid ${BRAND.tealBorder};
    box-shadow: 0 1px 12px rgba(15,76,92,0.06);
  }

  .sd-nav-brand {
    display: flex; align-items: center; gap: 10px;
  }

  .sd-nav-title {
    font-family: 'Poppins', sans-serif;
    font-weight: 800; font-size: 17px;
    background: linear-gradient(90deg, ${BRAND.deepTeal}, ${BRAND.aquaTeal});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.3px;
  }

  .sd-nav-sub {
    font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase;
    color: ${BRAND.textFaint};
  }

  .sd-nav-items {
    display: flex; align-items: center; gap: 2px;
  }

  .sd-nav-btn {
    background: none; border: none; cursor: pointer;
    padding: 8px 16px; border-radius: 8px;
    font-family: 'Inter', sans-serif;
    font-size: 17px; font-weight: 500;
    color: ${BRAND.textMuted};
    transition: color 0.2s, background 0.2s;
    position: relative;
  }

  .sd-nav-btn:hover { color: ${BRAND.deepTeal}; background: ${BRAND.tealLight}; }

  .sd-nav-btn.active {
    color: ${BRAND.deepTeal}; font-weight: 600;
    background: ${BRAND.tealLight};
  }

  .sd-alert-badge {
    position: absolute; top: 4px; right: 6px;
    width: 16px; height: 16px; border-radius: 50%;
    background: ${BRAND.red}; color: #fff;
    font-size: 9px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
  }

  /* ── Main layout ── */
  .sd-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 16px 20px;
    overflow: hidden;
    min-height: 0;
    height: calc(100vh - 85px);
    box-sizing: border-box;
  }

  /* ── Page header ── */
  .sd-page-header {
    background: ${BRAND.surface};
    border-radius: 14px;
    border: 1px solid ${BRAND.borderLight};
    overflow: hidden;
    flex-shrink: 0;
    box-shadow: 0 2px 10px rgba(15,76,92,0.05);
  }

  .sd-header-top {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 22px 14px;
  }

  .sd-header-title {
    font-family: 'Poppins', sans-serif;
    font-size: 20px; font-weight: 700;
    color: ${BRAND.deepTeal}; letter-spacing: -0.3px;
  }

  .sd-header-sub {
    font-size: 13px; color: ${BRAND.aquaTeal};
    margin-top: 2px; font-weight: 500;
  }

  .sd-select {
    padding: 7px 12px;
    border: 1px solid ${BRAND.tealBorder2};
    border-radius: 8px;
    font-family: 'Inter', sans-serif;
    font-size: 13px; color: ${BRAND.textBody};
    background: ${BRAND.offWhite};
    cursor: pointer;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .sd-select:focus {
    border-color: ${BRAND.aquaTeal};
    box-shadow: 0 0 0 3px rgba(46,196,182,0.12);
  }

  .sd-refresh-btn {
    width: 34px; height: 34px;
    border: 1px solid ${BRAND.borderMid};
    border-radius: 8px; background: none;
    cursor: pointer; color: ${BRAND.textMuted};
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; transition: all 0.2s;
  }
  .sd-refresh-btn:hover {
    border-color: ${BRAND.aquaTeal};
    color: ${BRAND.aquaTeal};
    background: ${BRAND.tealLight};
  }

  /* Student identity bar */
  .sd-student-bar {
    border-top: 1px solid rgba(46,196,182,0.1);
    border-left: 4px solid ${BRAND.aquaTeal};
    padding: 14px 22px;
    display: flex; align-items: center; gap: 16px;
    background: linear-gradient(90deg, rgba(46,196,182,0.05) 0%, transparent 60%);
    animation: fadeUp 0.4s ease both;
  }

  .sd-avatar {
    width: 50px; height: 50px; border-radius: 50%; flex-shrink: 0;
    border: 2px solid ${BRAND.tealBorder2};
    background: linear-gradient(135deg, ${BRAND.deepTeal}, ${BRAND.aquaTeal});
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
  }

  .sd-student-name {
    font-family: 'Poppins', sans-serif;
    font-size: 17px; font-weight: 700; color: ${BRAND.deepTeal};
  }

  .sd-school-badge {
    background: rgba(111,190,220,0.18); color: ${BRAND.deepTeal};
    font-size: 11px; font-weight: 700; padding: 3px 9px;
    border-radius: 4px; letter-spacing: 0.04em;
  }

  .sd-meta { font-size: 12px; color: ${BRAND.textMuted}; }

  .sd-risk-pill {
    font-size: 12px; font-weight: 700;
    padding: 6px 14px; border-radius: 8px;
  }

  .sd-profile-btn {
    display: flex; align-items: center; gap: 6px;
    border: 1px solid ${BRAND.borderMid};
    background: #fff; border-radius: 8px;
    padding: 7px 14px; cursor: pointer;
    font-family: 'Inter', sans-serif;
    font-size: 13px; font-weight: 500;
    color: ${BRAND.textBody};
    transition: all 0.2s;
  }
  .sd-profile-btn:hover {
    border-color: ${BRAND.aquaTeal}; color: ${BRAND.deepTeal};
    box-shadow: 0 2px 8px rgba(46,196,182,0.12);
  }

  /* ── Content grid ── */
  .sd-content-grid {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 14px;
    flex: 1;
    min-height: 0;
  }

  /* ── Left column ── */
  .sd-left {
    display: flex; flex-direction: column; gap: 14px;
    min-height: 0; overflow-y: auto;
  }

  /* ── Cards (shared) ── */
  .sd-card {
    background: ${BRAND.surface};
    border-radius: 14px;
    border: 1px solid ${BRAND.borderLight};
    padding: 20px;
    box-shadow: 0 2px 10px rgba(15,76,92,0.04);
    transition: box-shadow 0.25s;
  }
  .sd-card:hover {
    box-shadow: 0 4px 20px rgba(15,76,92,0.08);
  }

  .sd-card-title {
    font-family: 'Poppins', sans-serif;
    font-size: 14px; font-weight: 700;
    color: ${BRAND.deepTeal}; margin-bottom: 14px;
  }

  /* ── Wellbeing score card ── */
  .sd-wb-score {
    font-family: 'Poppins', sans-serif;
    font-size: 52px; font-weight: 800;
    color: ${BRAND.deepTeal}; line-height: 1;
    margin: 8px 0 16px;
  }

  .sd-wb-track {
    position: relative; height: 10px; border-radius: 5px;
    background: linear-gradient(to right, ${BRAND.green}, ${BRAND.amber}, ${BRAND.red});
    margin-bottom: 8px; overflow: visible;
  }

  .sd-wb-cursor {
    position: absolute; top: 50%; width: 4px; height: 18px;
    background: ${BRAND.deepTeal}; border-radius: 2px;
    transform: translate(-50%, -50%);
  }

  .sd-wb-footer {
    display: flex; align-items: flex-start; gap: 8px;
    background: ${BRAND.offWhite}; border-radius: 10px; padding: 11px;
    border: 1px solid ${BRAND.borderLight};
    margin-top: 14px;
  }

  .sd-wb-footer-text { font-size: 12px; color: ${BRAND.textBody}; line-height: 1.5; }

  /* ── Intervention level ── */
  .sd-level-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 9px 12px; border-radius: 8px;
    margin-bottom: 4px; font-size: 13px;
    transition: background 0.2s;
  }

  /* ── Stat mini cards ── */
  .sd-stat-pair {
    display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
  }

  .sd-stat-mini {
    background: ${BRAND.surface}; border-radius: 12px;
    border: 1px solid ${BRAND.borderLight};
    padding: 16px; text-align: center;
    display: flex; flex-direction: column; align-items: center; gap: 6px;
    box-shadow: 0 1px 6px rgba(15,76,92,0.04);
  }

  .sd-stat-label { font-size: 11px; color: ${BRAND.textMuted}; }
  .sd-stat-val { font-size: 13px; font-weight: 700; color: ${BRAND.deepTeal}; }

  /* ── Right column ── */
  .sd-right {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 14px;
    min-height: 0;
    overflow: hidden;
  }

  /* ── Trait bars ── */
  .sd-trait-bar-row { margin-bottom: 7px; }
  .sd-trait-bar-labels {
    display: flex; justify-content: space-between;
    margin-bottom: 3px;
  }
  .sd-trait-name { font-size: 11px; color: ${BRAND.textMuted}; font-weight: 500; }
  .sd-trait-val  { font-size: 11px; font-weight: 700; }

  .sd-bar-track {
    width: 100%; height: 5px; background: ${BRAND.offWhite};
    border-radius: 3px; overflow: hidden;
    border: 1px solid ${BRAND.borderLight};
  }

  .sd-bar-fill {
    height: 100%; border-radius: 3px;
    transition: width 0.7s ease;
  }

  /* ── Gaze indicator ── */
  .sd-gaze-box {
    background: ${BRAND.offWhite}; border-radius: 8px;
    padding: 10px 12px; border: 1px solid ${BRAND.borderLight};
    margin-top: 10px;
  }

  .sd-gaze-label {
    font-size: 10px; font-weight: 700; color: ${BRAND.textFaint};
    letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 7px;
  }

  /* ── Emotion rows ── */
  .sd-emotion-row {
    display: flex; align-items: center; gap: 8px; margin-bottom: 5px;
  }

  /* ── Session history ── */
  .sd-session-span { grid-column: 1 / -1; overflow-y: auto; }

  .sd-session-row {
    display: flex; align-items: center; gap: 14px;
    padding: 11px 0;
    border-bottom: 1px solid ${BRAND.offWhite};
    transition: background 0.15s; border-radius: 6px;
    cursor: pointer;
  }
  .sd-session-row:hover { background: ${BRAND.offWhite}; padding-left: 6px; }
  .sd-session-row:last-child { border-bottom: none; }

  .sd-session-icon {
    width: 36px; height: 36px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; color: #fff; flex-shrink: 0;
  }

  /* ── Loading states ── */
  .sd-skeleton {
    background: linear-gradient(90deg, ${BRAND.offWhite} 25%, rgba(46,196,182,0.08) 50%, ${BRAND.offWhite} 75%);
    background-size: 200% auto;
    animation: shimmer 1.6s linear infinite;
    border-radius: 6px;
  }

  /* ── Live dot ── */
  .sd-live-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: ${BRAND.green};
    animation: liveDot 1.4s ease-in-out infinite;
  }

  /* ── School summary dividers ── */
  .sd-school-row {
    display: flex; justify-content: space-between;
    padding: 7px 0; border-bottom: 1px solid ${BRAND.offWhite};
    font-size: 12px;
  }
  .sd-school-row:last-child { border-bottom: none; }

  /* ── Status badge ── */
  .sd-status-badge {
    font-size: 11px; font-weight: 700; padding: 3px 9px;
    border-radius: 6px;
  }

  /* ── User area ── */
  .sd-user-area {
    display: flex; align-items: center; gap: 12px;
  }

 .sd-tracked-pill {
    display: flex; align-items: center; gap: 7px;
    background: rgba(34,197,94,0.08);
    color: ${BRAND.green};
    border-radius: 20px; padding: 8px 16px;
    font-size: 14px; font-weight: 600;}

  .sd-user-email {
    font-size: 16px; font-weight: 600; color: ${BRAND.deepTeal};
  }

  /* ── Scan card ── */
  .sd-scan-card {
    border-radius: 12px; overflow: hidden; position: relative;
    border: 1px solid ${BRAND.tealBorder2};
    animation: glowPulse 3s ease-in-out infinite;
  }

  .sd-scan-line {
    position: absolute; left: 0; right: 0; height: 1.5px;
    background: linear-gradient(90deg, transparent, ${BRAND.aquaTeal}, transparent);
    animation: scanLine 3.5s ease-in-out infinite;
    box-shadow: 0 0 8px rgba(46,196,182,0.7);
    top: 6%;
  }

  .sd-scan-corner {
    position: absolute; width: 16px; height: 16px;
    border-color: ${BRAND.aquaTeal}; border-style: solid; border-width: 0;
  }
  .sd-scan-corner.tl { top: 10px; left: 10px; border-top-width: 2px; border-left-width: 2px; }
  .sd-scan-corner.tr { top: 10px; right: 10px; border-top-width: 2px; border-right-width: 2px; }
  .sd-scan-corner.bl { bottom: 10px; left: 10px; border-bottom-width: 2px; border-left-width: 2px; }
  .sd-scan-corner.br { bottom: 10px; right: 10px; border-bottom-width: 2px; border-right-width: 2px; }

  /* Responsive */
  @media (max-width: 1100px) {
    .sd-content-grid { grid-template-columns: 1fr; }
    .sd-right { grid-template-columns: 1fr 1fr; }
  }
  @media (max-width: 720px) {
    .sd-right { grid-template-columns: 1fr; }
    .sd-main { padding: 10px; }
  }
`;

// ─── Trait config ─────────────────────────────────────────────────────────────
const TRAIT_LABELS = {
  emotional_positivity: "Emotional Positivity",
  stress_resilience:    "Stress Resilience",
  social_engagement:    "Social Engagement",
  social_confidence:    "Social Confidence",
  physical_energy:      "Physical Energy",
  posture_health:       "Posture Health",
  body_openness:        "Body Openness",
  focus_alertness:      "Focus & Alertness",
  facial_relaxation:    "Facial Relaxation",
  vitality_glow:        "Vitality & Glow",
};

// SVG icons for traits — no emojis
const TRAIT_ICONS = {
  emotional_positivity: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><circle cx="9" cy="9" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="9" r="1" fill="currentColor" stroke="none"/></svg>
  ),
  stress_resilience: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
  ),
  social_engagement: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>
  ),
  social_confidence: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
  ),
  physical_energy: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
  ),
  posture_health: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="5" r="2"/><path d="M12 7v8M9 10h6M9 19l3-4 3 4"/></svg>
  ),
  body_openness: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 11V6a2 2 0 00-2-2v0a2 2 0 00-2 2v0M14 10V4a2 2 0 00-2-2v0a2 2 0 00-2 2v2M10 10.5V6a2 2 0 00-2-2v0a2 2 0 00-2 2v8"/><path d="M6 14v0a4 4 0 004 4h4a4 4 0 004-4v-5"/></svg>
  ),
  focus_alertness: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="3"/><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/></svg>
  ),
  facial_relaxation: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/><circle cx="9" cy="9" r="0.5" fill="currentColor" stroke="none"/><circle cx="15" cy="9" r="0.5" fill="currentColor" stroke="none"/></svg>
  ),
  vitality_glow: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
  ),
};

const EMOTION_COLORS = {
  happy:   BRAND.aquaTeal,
  neutral: BRAND.softBlue,
  sad:     "#6FBEDC",
  angry:   BRAND.red,
  fear:    BRAND.amber,
  surprise:"#a855f7",
  disgust: "#78716c",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
function wellbeingColor(s) {
  return s >= 70 ? BRAND.green : s >= 50 ? BRAND.amber : BRAND.red;
}

function wellbeingLabel(s) {
  if (s >= 70) return "Flourishing";
  if (s >= 60) return "Stable";
  if (s >= 45) return "Settling";
  return "Needs Support";
}

function riskLevel(s) {
  if (s >= 70) return { label: "Low Risk",      color: BRAND.green, bg: "rgba(34,197,94,0.08)"  };
  if (s >= 50) return { label: "Moderate",      color: BRAND.amber, bg: "rgba(245,158,11,0.08)" };
  return              { label: "High Priority",  color: BRAND.red,   bg: "rgba(239,68,68,0.08)"  };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function TraitBar({ label, icon, value }) {
  const color = value >= 70 ? BRAND.green : value >= 45 ? BRAND.amber : BRAND.red;
  return (
    <div className="sd-trait-bar-row">
      <div className="sd-trait-bar-labels">
        <span className="sd-trait-name" style={{ display: "flex", alignItems: "center", gap: 4, color: BRAND.textMuted }}>
          <span style={{ color }}>{icon}</span>{label}
        </span>
        <span className="sd-trait-val" style={{ color }}>{value}%</span>
      </div>
      <div className="sd-bar-track">
        <div className="sd-bar-fill" style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  );
}

function GazeIndicator({ gaze }) {
  if (!gaze) return null;
  const dir  = gaze.gaze_direction || "forward";
  const attn = gaze.attention_score || 50;
  const gh   = Math.max(-1, Math.min(1, gaze.gaze_horizontal || 0));
  const gv   = Math.max(-1, Math.min(1, gaze.gaze_vertical   || 0));
  const irisX = 50 + gh * 28;
  const irisY = 50 + gv * 28;
  const attnColor = attn >= 70 ? BRAND.green : attn >= 45 ? BRAND.amber : BRAND.red;

  return (
    <div className="sd-gaze-box">
      <div className="sd-gaze-label">Gaze & Attention</div>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {/* Eye tracker */}
        <div style={{ width: 48, height: 32, background: "rgba(111,190,220,0.1)", border: `1.5px solid ${BRAND.tealBorder2}`, borderRadius: 20, position: "relative", overflow: "hidden", flexShrink: 0 }}>
          <div style={{ width: 11, height: 11, background: BRAND.aquaTeal, borderRadius: "50%", position: "absolute", left: `calc(${irisX}% - 5.5px)`, top: `calc(${irisY}% - 5.5px)`, transition: "all 0.3s", boxShadow: `0 0 0 2px rgba(46,196,182,0.2)` }} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, flexWrap: "wrap" }}>
            <span style={{ padding: "2px 7px", borderRadius: 4, fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", background: dir === "forward" ? "rgba(34,197,94,0.1)" : "rgba(245,158,11,0.1)", color: dir === "forward" ? BRAND.green : BRAND.amber }}>
              {dir}
            </span>
            {gaze.focus_zone && <span style={{ fontSize: 10, color: BRAND.textFaint }}>zone: <b>{gaze.focus_zone}</b></span>}
            {gaze.eye_contact && <span style={{ fontSize: 10, color: BRAND.green, fontWeight: 600 }}>Eye contact</span>}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 10, color: BRAND.textFaint }}>Attention</span>
            <div style={{ width: 60, height: 4, background: BRAND.offWhite, borderRadius: 2, overflow: "hidden" }}>
              <div style={{ width: `${attn}%`, height: "100%", background: attnColor, borderRadius: 2 }} />
            </div>
            <span style={{ fontSize: 10, fontWeight: 700, color: attnColor }}>{attn}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function InterventionLevel({ wellbeingScore }) {
  const levels = [
    { label: "Level 0 — Flourishing",    range: [70, 100] },
    { label: "Level 1 — Stable",         range: [55,  70] },
    { label: "Level 2 — Settling",       range: [40,  55] },
    { label: "Level 3 — Needs Support",  range: [ 0,  40] },
  ];
  const current = levels.find(l => wellbeingScore >= l.range[0] && wellbeingScore <= l.range[1]) || levels[3];

  return (
    <div className="sd-card" style={{ flex: 1 }}>
      <div className="sd-card-title">Intervention Level</div>
      {levels.map((l, i) => {
        const isActive = l.label === current.label;
        return (
          <div key={i} className="sd-level-row" style={{
            background:  isActive ? "rgba(46,196,182,0.08)" : "transparent",
            color:       isActive ? BRAND.deepTeal : BRAND.textFaint,
            fontWeight:  isActive ? 600 : 400,
            fontSize:    13,
            borderLeft:  isActive ? `3px solid ${BRAND.aquaTeal}` : "3px solid transparent",
          }}>
            <span>{l.label}</span>
            {isActive && (
              <span style={{ fontSize: 10, fontWeight: 700, color: BRAND.aquaTeal, background: "rgba(46,196,182,0.1)", padding: "2px 8px", borderRadius: 5 }}>
                Current
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function SessionHistory({ sessions }) {
  if (!sessions || sessions.length === 0) return (
    <div className="sd-card sd-session-span">
      <div className="sd-card-title">Session History</div>
      <p style={{ fontSize: 13, color: BRAND.textFaint }}>No session data available.</p>
    </div>
  );

  const sessionColors = [BRAND.aquaTeal, BRAND.softBlue, BRAND.deepTeal, "#a855f7"];

  return (
    <div className="sd-card sd-session-span" style={{ overflow: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
        <div>
          <div className="sd-card-title" style={{ marginBottom: 2 }}>Session History</div>
          <div style={{ fontSize: 11, color: BRAND.textFaint }}>Detection dates for this student</div>
        </div>
        <span style={{ fontSize: 11, color: BRAND.textMuted, fontWeight: 500 }}>{sessions.length} sessions</span>
      </div>
      <div>
        {sessions.map((s, i) => (
          <div key={i} className="sd-session-row">
            <div className="sd-session-icon" style={{ background: sessionColors[i % sessionColors.length] }}>
              {s.date?.slice(8, 10) || i + 1}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: BRAND.deepTeal }}>{s.date}</div>
              <div className="sd-meta" style={{ marginTop: 2 }}>
                Wellbeing: {s.wellbeing}% · Emotion: {s.emotion} · Attention: {s.attention}%
              </div>
            </div>
            <span className="sd-status-badge" style={{ color: wellbeingColor(s.wellbeing), background: `${wellbeingColor(s.wellbeing)}18` }}>
              {wellbeingLabel(s.wellbeing)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Brand nav logo SVG ───────────────────────────────────────────────────────
function BrandIcon() {
  return (
    <div style={{ width: 36, height: 36, borderRadius: 10, background: "rgba(46,196,182,0.1)", border: `1px solid ${BRAND.tealBorder2}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
      <svg width="20" height="20" viewBox="0 0 64 64" fill="none">
        <path d="M22 28c0-5.523 4.477-10 10-10s10 4.477 10 10c0 1.5-.33 2.92-.918 4.194C43.012 33.36 44 35.07 44 37c0 3.314-2.686 6-6 6a5.98 5.98 0 01-3-.798A5.98 5.98 0 0132 43a5.98 5.98 0 01-3 .798A6 6 0 0120 37c0-1.93.988-3.64 2.918-4.806A9.96 9.96 0 0122 28z" fill="rgba(46,196,182,0.2)" stroke={BRAND.aquaTeal} strokeWidth="2" strokeLinejoin="round" />
        <path d="M32 18v25M22 28c3 0 5 2 5 5s-2 4-5 4M42 28c-3 0-5 2-5 5s2 4 5 4" stroke={BRAND.aquaTeal} strokeWidth="2" strokeLinecap="round" />
        <circle cx="32" cy="28" r="3" fill={BRAND.aquaTeal} />
      </svg>
    </div>
  );
}

// ─── Skeleton loader ──────────────────────────────────────────────────────────
function SkeletonDash() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14, padding: 2 }}>
      <div className="sd-skeleton" style={{ height: 100, borderRadius: 14 }} />
      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 14 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[160, 120, 80].map((h, i) => <div key={i} className="sd-skeleton" style={{ height: h, borderRadius: 14 }} />)}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {[1,2,3,4].map(i => <div key={i} className="sd-skeleton" style={{ borderRadius: 14 }} />)}
        </div>
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
const BehaviourIntelligenceDashboard = () => {
  const { user } = useSession();
  const [activeNav,        setActiveNav]        = useState("Principal");
  const [report,           setReport]           = useState(null);
  const [selectedPersonId, setSelectedPersonId] = useState(null);
  const [loading,          setLoading]          = useState(true);
  const [error,            setError]            = useState(null);

  const navItems = ["Principal", "Dashboard", "Alerts", "Settings"];

  useEffect(() => { fetchReport(); }, []);

  async function fetchReport() {
    setLoading(true); setError(null);
    try {
      const res  = await apiFetch("/get_report");
      const data = await res.json();
      if (data.success && data.report) {
        setReport(data.report);
        const persons = Object.values(data.report.person_profiles || {});
        if (persons.length > 0) setSelectedPersonId(persons[0].person_id);
      } else {
        setError("No report available. Run the analysis first.");
      }
    } catch {
      setError(`Cannot connect to backend at ${API_BASE}. Make sure the Flask server is running.`);
    }
    setLoading(false);
  }

  const persons        = report ? Object.values(report.person_profiles || {}) : [];
  const selectedPerson = persons.find(p => p.person_id === selectedPersonId) || persons[0] || null;
  const latestPoint    = selectedPerson?.temporal_series?.at(-1) || {};
  const latestGaze     = latestPoint.gaze
    ? { gaze_direction: latestPoint.gaze, attention_score: latestPoint.attention || 50, focus_zone: latestPoint.focus_zone || "ahead" }
    : null;

  const sessionsByDate = {};
  (selectedPerson?.temporal_series || []).forEach(pt => {
    if (!sessionsByDate[pt.date]) sessionsByDate[pt.date] = { date: pt.date, wellbeings: [], attentions: [] };
    sessionsByDate[pt.date].wellbeings.push(pt.wellbeing);
    sessionsByDate[pt.date].attentions.push(pt.attention || 50);
  });
  const sessions = Object.values(sessionsByDate).map(s => ({
    date:      s.date,
    wellbeing: Math.round(s.wellbeings.reduce((a, v) => a + v, 0) / s.wellbeings.length),
    emotion:   latestPoint.gaze || "neutral",
    attention: Math.round(s.attentions.reduce((a, v) => a + v, 0) / s.attentions.length),
  })).sort((a, b) => a.date.localeCompare(b.date));

  const traits      = selectedPerson?.avg_traits || {};
  const wellbeing   = selectedPerson?.average_wellbeing || 0;
  const engagement  = selectedPerson?.average_engagement || 0;
  const risk        = riskLevel(wellbeing);
  const atRiskCount = persons.filter(p => p.average_wellbeing < 50).length;

  const renderContent = () => {
    if (loading) return <SkeletonDash />;

    if (error) return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flex: 1, flexDirection: "column", gap: 14, padding: 40 }}>
        <div style={{ width: 48, height: 48, borderRadius: 12, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={BRAND.red} strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><circle cx="12" cy="16" r="1" fill={BRAND.red} stroke="none"/></svg>
        </div>
        <div style={{ fontSize: 16, fontWeight: 700, color: BRAND.deepTeal }}>Connection Error</div>
        <div style={{ fontSize: 13, color: BRAND.textMuted, textAlign: "center", maxWidth: 400, lineHeight: 1.6 }}>{error}</div>
        <button onClick={fetchReport} style={{ marginTop: 4, padding: "9px 22px", background: `linear-gradient(90deg, ${BRAND.deepTeal}, ${BRAND.aquaTeal})`, color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer", transition: "opacity 0.2s" }}
          onMouseOver={e => e.target.style.opacity = "0.88"} onMouseOut={e => e.target.style.opacity = "1"}>
          Retry
        </button>
      </div>
    );

    if (!selectedPerson) return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flex: 1 }}>
        <div style={{ fontSize: 14, color: BRAND.textFaint }}>No person data found. Run analysis first.</div>
      </div>
    );

    return (
      <>
        {/* ── Page Header ─────────────────────────────────────────────────── */}
        <div className="sd-page-header">
          <div className="sd-header-top">
            <div>
              <div className="sd-header-title">Student Overview</div>
              <div className="sd-header-sub">
                {report?.overall_stats?.total_unique_persons || 0} persons tracked
                · {report?.overall_stats?.total_dates_analyzed || 0} days
                · {report?.overall_stats?.total_schools || 0} school(s)
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <select className="sd-select" value={selectedPersonId || ""} onChange={e => setSelectedPersonId(e.target.value)}>
                {persons.map(p => (
                  <option key={p.person_id} value={p.person_id}>{p.name} ({p.school})</option>
                ))}
              </select>
              <button className="sd-refresh-btn" onClick={fetchReport} title="Refresh">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M1 4v6h6M23 20v-6h-6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
              </button>
            </div>
          </div>

          {/* Student bar */}
          <div className="sd-student-bar">
            <div className="sd-avatar">
              {selectedPerson.profile_image
                ? <img src={`data:image/jpeg;base64,${selectedPerson.profile_image}`} alt={selectedPerson.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                : <svg width="24" height="24" viewBox="0 0 24 24" fill="rgba(247,249,251,0.9)"><path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z" /></svg>
              }
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span className="sd-student-name">{selectedPerson.name}</span>
                <span className="sd-school-badge">{selectedPerson.school}</span>
                <span className="sd-meta">· {selectedPerson.total_detections} detections · {selectedPerson.days_present} days</span>
              </div>
              <div style={{ display: "flex", gap: 16, marginTop: 3 }}>
                <span className="sd-meta">ID: {selectedPerson.person_id}</span>
                <span className="sd-meta">First: {selectedPerson.dates_seen?.[0] || "—"}</span>
                <span className="sd-meta">Last: {selectedPerson.dates_seen?.at(-1) || "—"}</span>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button className="sd-profile-btn">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                View Profile
              </button>
              <div className="sd-risk-pill" style={{ color: risk.color, background: risk.bg }}>
                {risk.label}
              </div>
            </div>
          </div>
        </div>

        {/* ── Content grid ─────────────────────────────────────────────────── */}
        <div className="sd-content-grid">

          {/* LEFT COLUMN */}
          <div className="sd-left">

            {/* Wellbeing Score */}
            <div className="sd-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill={BRAND.amber}><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
                  <span className="sd-card-title" style={{ marginBottom: 0 }}>Wellbeing Score</span>
                </div>
                <span className="sd-risk-pill" style={{ color: risk.color, background: risk.bg, fontSize: 11 }}>{risk.label}</span>
              </div>

              <div className="sd-wb-score">{wellbeing}%</div>

              <div className="sd-wb-track">
                <div className="sd-wb-cursor" style={{ left: `${Math.min(wellbeing, 98)}%` }} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: BRAND.textFaint, marginBottom: 0 }}>
                <span>Overall Score</span>
                <span>{selectedPerson.days_present}d tracked</span>
              </div>

              <div className="sd-wb-footer">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={BRAND.aquaTeal} strokeWidth="2.5" style={{ marginTop: 1, flexShrink: 0 }}><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>
                <span className="sd-wb-footer-text">
                  Engagement: {engagement}% · Dominant gaze: {selectedPerson.dominant_gaze || "—"}
                </span>
              </div>
            </div>

            {/* Intervention Level */}
            <InterventionLevel wellbeingScore={wellbeing} />

            {/* Stat mini-pair */}
            <div className="sd-stat-pair">
              <div className="sd-stat-mini">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={BRAND.aquaTeal} strokeWidth="1.5" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                <div className="sd-stat-label">First Seen</div>
                <div className="sd-stat-val">{selectedPerson.dates_seen?.[0] || "—"}</div>
              </div>
              <div className="sd-stat-mini">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={BRAND.aquaTeal} strokeWidth="1.5" strokeLinecap="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                <div className="sd-stat-label">Detections</div>
                <div className="sd-stat-val" style={{ fontSize: 16 }}>{selectedPerson.total_detections}</div>
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN */}
          <div className="sd-right">

            {/* Trait Analysis */}
            <div className="sd-card" style={{ overflow: "auto" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <div className="sd-card-title" style={{ marginBottom: 0 }}>Trait Analysis</div>
                <span className="sd-risk-pill" style={{ color: risk.color, background: risk.bg, fontSize: 11 }}>{risk.label}</span>
              </div>
              <div>
                {Object.entries(TRAIT_LABELS).map(([key, label]) => (
                  <TraitBar key={key} label={label} icon={TRAIT_ICONS[key]} value={traits[key] ?? 50} />
                ))}
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginTop: 14, padding: "9px 12px", background: wellbeing >= 50 ? "rgba(34,197,94,0.06)" : "rgba(239,68,68,0.06)", borderRadius: 8, border: `1px solid ${wellbeing >= 50 ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)"}` }}>
                <span style={{ fontSize: 12, color: wellbeing >= 50 ? BRAND.green : BRAND.red, fontWeight: 500 }}>
                  {wellbeing >= 70 ? "No acute immediate risk" : wellbeing >= 50 ? "Monitor closely" : "Needs support"}
                </span>
              </div>
            </div>

            {/* Gaze & Emotion */}
            <div className="sd-card" style={{ display: "flex", flexDirection: "column", overflow: "auto" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <div className="sd-card-title" style={{ marginBottom: 0 }}>Gaze & Emotion</div>
                <span style={{ fontSize: 13, fontWeight: 600, color: BRAND.textBody }}>{selectedPerson.dominant_gaze || "—"}</span>
              </div>

              {latestGaze && <GazeIndicator gaze={latestGaze} />}

              {/* Latest emotion state */}
              {latestPoint && (
                <div style={{ marginTop: 12, padding: 12, background: BRAND.offWhite, borderRadius: 10, border: `1px solid ${BRAND.borderLight}` }}>
                  <div className="sd-gaze-label" style={{ marginBottom: 8 }}>Latest Emotion State</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ width: 38, height: 38, borderRadius: 10, background: "rgba(46,196,182,0.1)", border: `1px solid ${BRAND.tealBorder}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      {/* SVG emotion indicator instead of emoji */}
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={EMOTION_COLORS[latestPoint.gaze] || BRAND.aquaTeal} strokeWidth="2" strokeLinecap="round">
                        <circle cx="12" cy="12" r="10"/>
                        {latestPoint.gaze === "happy"   && <path d="M8 14s1.5 2 4 2 4-2 4-2"/>}
                        {latestPoint.gaze === "sad"     && <path d="M16 16s-1.5-2-4-2-4 2-4 2"/>}
                        {latestPoint.gaze === "angry"   && <path d="M8 15s1.5-1.5 4-1.5 4 1.5 4 1.5M8 9l2 1M14 9l2-1"/>}
                        {!["happy","sad","angry"].includes(latestPoint.gaze) && <path d="M8 15h8"/>}
                        <circle cx="9" cy="9" r="1" fill="currentColor" stroke="none"/>
                        <circle cx="15" cy="9" r="1" fill="currentColor" stroke="none"/>
                      </svg>
                    </div>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: BRAND.deepTeal, textTransform: "capitalize" }}>{latestPoint.gaze || "Neutral"}</div>
                      <div className="sd-meta">Attention: {latestPoint.attention || 50}%</div>
                    </div>
                    <div style={{ marginLeft: "auto", fontSize: 22, fontWeight: 800, color: wellbeingColor(latestPoint.wellbeing || 50), fontFamily: "Poppins, sans-serif" }}>
                      {latestPoint.wellbeing || 50}%
                    </div>
                  </div>
                </div>
              )}

              {/* School summary */}
              <div style={{ marginTop: 14, flex: 1 }}>
                <div className="sd-gaze-label" style={{ marginBottom: 8 }}>School Summary</div>
                {(report?.overall_stats?.schools || []).map(school => {
                  const sp  = persons.filter(p => p.school === school);
                  const avg = sp.length ? Math.round(sp.reduce((a, p) => a + p.average_wellbeing, 0) / sp.length) : 0;
                  return (
                    <div key={school} className="sd-school-row">
                      <span style={{ color: BRAND.textBody, fontWeight: 500 }}>{school}</span>
                      <span style={{ fontWeight: 700, color: wellbeingColor(avg) }}>{avg}% avg</span>
                    </div>
                  );
                })}
                <div className="sd-school-row">
                  <span style={{ color: BRAND.textBody, fontWeight: 500 }}>At-risk persons</span>
                  <span style={{ fontWeight: 700, color: BRAND.red }}>{atRiskCount}</span>
                </div>
              </div>
            </div>

            {/* Session History — spans full width */}
            <SessionHistory sessions={sessions} />
          </div>
        </div>
      </>
    );
  };

  return (
    <div className="sentio-dash">
      <style>{GLOBAL_STYLE}</style>

      {/* ── NAV ──────────────────────────────────────────────────────────── */}
      <nav className="sd-nav">
        <img src={icon} alt="Sentio Mind" style={{ width: 210, height: 70 }} />
        <div style={{ flex: 1 }} />
        <div className="sd-nav-items">
        {navItems.map(item => (
            <button
              key={item}
              className={`sd-nav-btn${activeNav === item ? " active" : ""}`}
              onClick={() => setActiveNav(item)}
              style={{ position: "relative" }}
            >
              {item}
              {item === "Alerts" && atRiskCount > 0 && (
                <span className="sd-alert-badge">{atRiskCount}</span>
              )}
            </button>
          ))}
        </div>

        <div style={{ flex: 1 }} />
        <div className="sd-user-area">
          <div className="sd-tracked-pill">
            <div className="sd-live-dot" />
            {loading ? "Loading..." : `${persons.length} tracked`}
          </div>
          <div>
            <div className="sd-user-email">Supervisor</div>
          </div>
          <LogoutButton />
        </div>
      </nav>

      {/* ── MAIN ─────────────────────────────────────────────────────────── */}
      <main className="sd-main">
        {renderContent()}
      </main>
    </div>
  );
};

export default BehaviourIntelligenceDashboard;