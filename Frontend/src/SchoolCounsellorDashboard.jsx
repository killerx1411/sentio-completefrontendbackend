/**
 * Sentio Mind — Counsellor Dashboard
 * Mirrors PrincipalDashboard.jsx exactly:
 *   - Same brand tokens (Deep Teal / Aqua Teal / Soft Blue / Off White / Charcoal)
 *   - Same Poppins + DM Sans typography
 *   - Same /get_report backend call + fetchReport pattern
 *   - Same session context + LogoutButton
 *   - Same card / KPI / heat-grid / trait-bar / avatar component style
 *
 * Report shape consumed (per person):
 * {
 *   person_id, name, average_engagement, average_wellbeing,
 *   days_present, dominant_gaze, pinned, profile_image,
 *   dates_seen: string[],
 *   avg_traits: { [key: string]: number },
 *   wellbeing_trend?: number[],
 *   temporal_series?: { date: string, wellbeing: number, traits: object }[]
 * }
 */

import { useState, useEffect, useRef, useCallback } from "react";
import LogoutButton from "./components/LogoutButton";
import { useSession } from "./context/SessionContext";
import icon from "./assets/icon.png";
// ─── Backend (mirrors Principal) ──────────────────────────────────────────────
import { apiFetch } from "./utils/api";

// ─── Brand tokens (identical to Principal) ────────────────────────────────────
const C = {
  deepTeal:    "#0F4C5C",
  aquaTeal:    "#2EC4B6",
  softBlue:    "#6FBEDC",
  offWhite:    "#F7F9FB",
  charcoal:    "#3A3F45",
  border:      "rgba(46,196,182,0.14)",
  borderHover: "rgba(46,196,182,0.40)",
  muted:       "#7A8899",
  danger:      "#D0454C",
  warn:        "#C47A2E",
  success:     "#2A8C72",
};

// ─── Global CSS (mirrors Principal's GLOBAL_CSS) ──────────────────────────────
const GLOBAL_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800&family=DM+Sans:wght@300;400;500;600&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  .sm-dash {
    font-family: 'DM Sans', sans-serif;
    background: ${C.offWhite};
    color: ${C.charcoal};
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .sm-dash ::-webkit-scrollbar { width: 5px; }
  .sm-dash ::-webkit-scrollbar-track { background: #e0f2fe; }
  .sm-dash ::-webkit-scrollbar-thumb { background: ${C.aquaTeal}; border-radius: 3px; }

  /* ── Navbar ── */
  .sm-nav {
    background: rgba(247,249,251,0.92);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border-bottom: 1px solid ${C.border};
    display: flex;
    align-items: center;
    padding: 0 32px;
    height: 95px;
    gap: 28px;
    flex-shrink: 0;
    position: relative;
    z-index: 10;
  }
  .sm-nav-logo {
    font-family: 'Poppins', sans-serif;
    font-weight: 800;
    font-size: 22px;
    background: linear-gradient(90deg, ${C.deepTeal}, ${C.aquaTeal});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.3px;
    white-space: nowrap;
  }
  .sm-nav-sub {
    font-size: 9px;
    color: ${C.muted};
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 1px;
  }
  .sm-nav-link {
    font-size: 17px;
    font-weight: 500;
    color: ${C.muted};
    text-decoration: none;
    padding-bottom: 4px;
    border-bottom: 2px solid transparent;
    transition: color 0.2s, border-color 0.2s;
    white-space: nowrap;
    cursor: pointer;
    background: none;
    border-top: none;
    border-left: none;
    border-right: none;
    outline: none;
    font-family: 'DM Sans', sans-serif;
  }
  .sm-nav-link:hover { color: ${C.deepTeal}; }
  .sm-nav-link.active {
    color: ${C.deepTeal};
    font-weight: 700;
    border-bottom-color: ${C.aquaTeal};
  }

  /* ── Body ── */
  .sm-body {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    padding: 20px 32px 20px;
  }

  /* ── KPI cards ── */
  .sm-kpi {
    background: #fff;
    border: 1px solid ${C.border};
    border-radius: 14px;
    padding: 16px 20px;
    transition: border-color 0.25s, box-shadow 0.25s;
  }
  .sm-kpi:hover {
    border-color: ${C.borderHover};
    box-shadow: 0 4px 20px rgba(15,76,92,0.07);
  }
  .sm-kpi-label {
    font-size: 10px;
    font-weight: 600;
    color: ${C.muted};
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 6px;
  }
  .sm-kpi-val {
    font-family: 'Poppins', sans-serif;
    font-size: 26px;
    font-weight: 800;
    line-height: 1;
    color: ${C.deepTeal};
  }
  .sm-kpi-sub { font-size: 11px; color: ${C.muted}; margin-top: 4px; }

  /* ── Cards ── */
  .sm-card {
    background: #fff;
    border: 1px solid ${C.border};
    border-radius: 16px;
    padding: 18px;
    transition: border-color 0.2s;
  }
  .sm-card:hover { border-color: ${C.borderHover}; }
  .sm-card-title {
    font-family: 'Poppins', sans-serif;
    font-size: 13px;
    font-weight: 700;
    color: ${C.deepTeal};
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 12px;
  }

  /* ── Trait bars ── */
  .sm-trait-row { margin-bottom: 9px; }
  .sm-trait-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
  .sm-trait-name { font-size: 11px; color: ${C.muted}; font-weight: 500; }
  .sm-trait-pct  { font-size: 11px; font-weight: 700; }
  .sm-bar-track  { width: 100%; height: 4px; background: #EEF3F6; border-radius: 2px; overflow: hidden; }
  .sm-bar-fill   { height: 100%; border-radius: 2px; transition: width 0.6s cubic-bezier(0.16,1,0.3,1); }

  /* ── Person row ── */
  .sm-person-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 6px;
    border-top: 1px solid #F0F4F7;
    cursor: pointer;
    border-radius: 8px;
    transition: background 0.15s, padding-left 0.15s;
  }
  .sm-person-row:hover { background: #F7FDFC; }
  .sm-person-row.selected { background: #EAF9F7; padding-left: 10px; }

  /* ── Heat grid cell ── */
  .sm-heat-cell {
    flex: 1;
    height: 24px;
    border-radius: 5px;
    transition: opacity 0.2s;
    cursor: pointer;
  }
  .sm-heat-cell:hover { opacity: 0.72; }

  /* ── Pill ── */
  .sm-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    border-radius: 100px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.03em;
  }
  .sm-pill-live    { background: rgba(42,140,114,0.10);  color: ${C.success}; }
  .sm-pill-warn    { background: rgba(196,122,46,0.10);  color: ${C.warn}; }
  .sm-pill-danger  { background: rgba(208,69,76,0.10);   color: ${C.danger}; }
  .sm-pill-info    { background: rgba(111,190,220,0.15); color: ${C.deepTeal}; }

  /* ── Risk panel ── */
  .sm-risk-panel {
    background: #FEF7F7;
    border: 1px solid rgba(208,69,76,0.2);
    border-radius: 10px;
    padding: 12px 14px;
    margin-top: 12px;
    flex-shrink: 0;
  }
  .sm-risk-label {
    font-size: 10px;
    font-weight: 700;
    color: ${C.danger};
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  /* ── Scroll ── */
  .sm-scroll { overflow-y: auto; flex: 1; min-height: 0; }

  /* ── Icon button ── */
  .sm-icon-btn {
    width: 34px; height: 34px;
    border: 1px solid ${C.border};
    border-radius: 9px;
    background: #fff;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: border-color 0.2s, background 0.2s;
    color: ${C.muted};
  }
  .sm-icon-btn:hover { border-color: ${C.aquaTeal}; background: rgba(46,196,182,0.05); color: ${C.deepTeal}; }

  /* ── Select ── */
  .sm-select {
    padding: 7px 14px;
    border: 1px solid ${C.border};
    border-radius: 9px;
    font-family: 'DM Sans', sans-serif;
    font-size: 12px;
    color: ${C.charcoal};
    background: #fff;
    cursor: pointer;
    outline: none;
    transition: border-color 0.2s;
  }
  .sm-select:hover { border-color: ${C.aquaTeal}; }

  /* ── Tab ── */
  .sm-tab {
    background: none;
    border: none;
    cursor: pointer;
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    padding-bottom: 10px;
    border-bottom: 2px solid transparent;
    color: ${C.muted};
    display: flex;
    align-items: center;
    gap: 5px;
    transition: color 0.2s, border-color 0.2s;
    white-space: nowrap;
  }
  .sm-tab:hover { color: ${C.deepTeal}; }
  .sm-tab.active { color: ${C.charcoal}; font-weight: 700; border-bottom-color: ${C.deepTeal}; }

  /* ── Animations ── */
  @keyframes smFadeUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .sm-reveal { animation: smFadeUp 0.55s cubic-bezier(0.16,1,0.3,1) both; }

  @keyframes smSpin { to { transform: rotate(360deg); } }
  @keyframes smPulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
  }
`;

// ─── Colour helpers (identical to Principal) ──────────────────────────────────
function wbColor(v) {
  if (v >= 70) return C.success;
  if (v >= 50) return C.aquaTeal;
  if (v >= 35) return C.warn;
  return C.danger;
}
function wbLabel(v) {
  if (v >= 70) return "Flourishing";
  if (v >= 60) return "Stable";
  if (v >= 45) return "Settling";
  return "Needs Support";
}
function barColor(v) {
  if (v >= 70) return C.success;
  if (v >= 45) return C.aquaTeal;
  return C.warn;
}
function heatColor(v) {
  if (v === null) return "#EEF3F6";
  if (v >= 70) return C.deepTeal;
  if (v >= 55) return C.aquaTeal;
  if (v >= 40) return C.softBlue;
  return "#B8DDE8";
}

// ─── Shared sub-components ────────────────────────────────────────────────────

function AvatarCircle({ name, image, size = 30, color }) {
  if (image) {
    return (
      <img
        src={image}
        alt={name}
        style={{ width: size, height: size, borderRadius: "50%", objectFit: "cover", flexShrink: 0 }}
        onError={(e) => { e.target.style.display = "none"; }}
      />
    );
  }
  const initials = (name || "?").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  return (
    <div style={{
      width: size, height: size, borderRadius: "50%", flexShrink: 0,
      background: color || `linear-gradient(135deg, ${C.deepTeal}, ${C.aquaTeal})`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: size > 26 ? 11 : 9, fontWeight: 700, color: "#fff", letterSpacing: "0.03em",
    }}>
      {initials}
    </div>
  );
}

function KpiCard({ label, value, sub, color, delay = 0 }) {
  return (
    <div className="sm-kpi sm-reveal" style={{ animationDelay: `${delay}s` }}>
      <div className="sm-kpi-label">{label}</div>
      <div className="sm-kpi-val" style={{ color: color || C.deepTeal }}>{value}</div>
      {sub && <div className="sm-kpi-sub">{sub}</div>}
    </div>
  );
}

function TraitBar({ label, value }) {
  const color = barColor(value);
  return (
    <div className="sm-trait-row">
      <div className="sm-trait-header">
        <span className="sm-trait-name">{label}</span>
        <span className="sm-trait-pct" style={{ color }}>{value}%</span>
      </div>
      <div className="sm-bar-track">
        <div className="sm-bar-fill" style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  );
}

function RefreshIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

// ─── Sparkline canvas ─────────────────────────────────────────────────────────
function SparklineCanvas({ student }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!student || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const W = canvas.offsetWidth;
    const H = 80;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, W, H);

    // Use wellbeing_trend if available, else synthesise from avg_traits values
    let data = student.wellbeing_trend && student.wellbeing_trend.length > 1
      ? student.wellbeing_trend
      : Object.values(student.avg_traits || {}).slice(0, 8);

    if (!data.length) return;

    const pad = { l: 10, r: 10, t: 14, b: 10 };
    const minV = Math.min(...data) - 5;
    const maxV = Math.max(...data) + 5;
    const toX = i => pad.l + (i / (data.length - 1)) * (W - pad.l - pad.r);
    const toY = v => pad.t + ((maxV - v) / (maxV - minV)) * (H - pad.t - pad.b);

    // Grid lines
    ctx.strokeStyle = "rgba(46,196,182,0.12)";
    ctx.lineWidth = 1;
    [25, 50, 75].forEach(v => {
      const y = toY(v);
      if (y >= pad.t && y <= H - pad.b) {
        ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
      }
    });

    // Fill gradient
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(data[0]));
    for (let i = 1; i < data.length; i++) {
      const cx = (toX(i - 1) + toX(i)) / 2;
      ctx.bezierCurveTo(cx, toY(data[i - 1]), cx, toY(data[i]), toX(i), toY(data[i]));
    }
    ctx.lineTo(toX(data.length - 1), H - pad.b);
    ctx.lineTo(toX(0), H - pad.b);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, pad.t, 0, H);
    grad.addColorStop(0, "rgba(46,196,182,0.22)");
    grad.addColorStop(1, "rgba(46,196,182,0)");
    ctx.fillStyle = grad;
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(data[0]));
    for (let i = 1; i < data.length; i++) {
      const cx = (toX(i - 1) + toX(i)) / 2;
      ctx.bezierCurveTo(cx, toY(data[i - 1]), cx, toY(data[i]), toX(i), toY(data[i]));
    }
    ctx.strokeStyle = C.aquaTeal;
    ctx.lineWidth = 2.5;
    ctx.lineJoin = "round";
    ctx.stroke();

    // Dots
    data.forEach((v, i) => {
      ctx.beginPath();
      ctx.arc(toX(i), toY(v), 4.5, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();
      ctx.strokeStyle = C.aquaTeal;
      ctx.lineWidth = 2;
      ctx.stroke();
      // value label
      ctx.font = `bold 8px 'DM Sans', sans-serif`;
      ctx.fillStyle = C.deepTeal;
      ctx.textAlign = "center";
      ctx.fillText(`${Math.round(v)}`, toX(i), toY(v) - 8);
    });
  }, [student]);

  return (
    <canvas
      ref={canvasRef}
      style={{ display: "block", width: "100%", height: 80 }}
    />
  );
}

// ─── Heat grid (weekly behaviour) ────────────────────────────────────────────
function HeatGrid({ persons }) {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  // Average trait values across persons per day-bucket (simplified: distribute traits across days)
  const traitKeys = persons.length ? Object.keys(persons[0].avg_traits || {}) : [];
  const rows = [0, 1, 2].map(ri =>
    days.map((_, ci) => {
      if (!persons.length) return null;
      const base = persons.reduce((a, p) => {
        const vals = Object.values(p.avg_traits || {});
        return a + (vals[ci % vals.length] || 50);
      }, 0) / persons.length;
      return Math.max(0, Math.min(100, base + (ri - 1) * 9));
    })
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {[2, 1, 0].map(ri => (
        <div key={ri} style={{ display: "flex", alignItems: "center", gap: 3 }}>
          <span style={{ fontSize: 9, color: C.muted, width: 12, textAlign: "right", marginRight: 3, flexShrink: 0 }}>{ri + 1}</span>
          {days.map((d, ci) => (
            <div
              key={ci}
              className="sm-heat-cell"
              style={{ background: heatColor(rows[ri][ci]) }}
              title={`${d}: ${rows[ri][ci] !== null ? Math.round(rows[ri][ci]) + "%" : "no data"}`}
            />
          ))}
        </div>
      ))}
      <div style={{ display: "flex", gap: 3, paddingLeft: 18, marginTop: 2 }}>
        {days.map(d => (
          <span key={d} style={{ fontSize: 9, color: C.muted, flex: 1, textAlign: "center" }}>{d}</span>
        ))}
      </div>
    </div>
  );
}

// ─── Main Counsellor Dashboard ────────────────────────────────────────────────
export default function CounsellorDashboard() {
  const { user } = useSession();

  // ── State ────────────────────────────────────────────────────────────────
  const [report, setReport]           = useState(null);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [activeNav, setActiveNav]     = useState("Dashboard");
  const [activeTab, setActiveTab]     = useState("Overview");
  const [selectedPerson, setSelected] = useState(null);
  const [searchQuery, setSearch]      = useState("");

  // ── Fetch (identical pattern to Principal) ───────────────────────────────
  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch("/get_report");
      const data = await res.json();
      if (data.success && data.report) {
        setReport(data.report);
        // Auto-select first person
        const profiles = Object.values(data.report.person_profiles || {});
        if (profiles.length) setSelected(profiles[0]);
      } else {
        setError("No report available. Run analysis first.");
      }
    } catch {
      setError("Cannot connect to backend. Make sure the Flask server is running.");
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchReport(); }, [fetchReport]);

  // ── Derived ──────────────────────────────────────────────────────────────
  const persons      = report ? Object.values(report.person_profiles) : [];
  const stats        = report?.overall_stats || {};
  const atRisk       = persons.filter(p => p.average_wellbeing < 50);
  const pinnedIds    = report?.pinned_profiles || [];

  const filtered = persons.filter(p =>
    !searchQuery || p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const sorted = [
    ...filtered.filter(p => pinnedIds.includes(p.person_id)),
    ...filtered.filter(p => !pinnedIds.includes(p.person_id))
      .sort((a, b) => b.average_wellbeing - a.average_wellbeing),
  ];

  const avgWb  = persons.length ? Math.round(persons.reduce((a, p) => a + p.average_wellbeing, 0) / persons.length) : 0;
  const avgEng = persons.length ? Math.round(persons.reduce((a, p) => a + p.average_engagement, 0) / persons.length) : 0;

  // Low traits for selected student
  const lowTraits = selectedPerson
    ? Object.entries(selectedPerson.avg_traits || {}).filter(([, v]) => v < 40).sort((a, b) => a[1] - b[1])
    : [];

  // ── Loading ──────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="sm-dash" style={{ alignItems: "center", justifyContent: "center", gap: 14 }}>
        <style>{GLOBAL_CSS}</style>
        <div style={{
          width: 32, height: 32, border: "2.5px solid #EEF3F6",
          borderTopColor: C.aquaTeal, borderRadius: "50%",
          animation: "smSpin 0.7s linear infinite",
        }} />
        <span style={{ fontSize: 13, color: C.muted }}>Loading report…</span>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="sm-dash" style={{ alignItems: "center", justifyContent: "center", gap: 12, padding: 40 }}>
        <style>{GLOBAL_CSS}</style>
        <div style={{ fontSize: 36 }}>⚠️</div>
        <div style={{ fontFamily: "'Poppins',sans-serif", fontSize: 16, fontWeight: 700, color: C.deepTeal }}>Connection Error</div>
        <div style={{ fontSize: 13, color: C.muted, textAlign: "center", maxWidth: 400 }}>{error}</div>
        <button
          onClick={fetchReport}
          style={{
            marginTop: 8, padding: "9px 22px",
            background: `linear-gradient(135deg, ${C.deepTeal}, ${C.aquaTeal})`,
            color: "#fff", border: "none", borderRadius: 10,
            fontSize: 14, fontWeight: 600, cursor: "pointer",
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="sm-dash">
      <style>{GLOBAL_CSS}</style>

      {/* ── NAVBAR ── */}
      <nav className="sm-nav">
        {/* Logo */}
        <img src={icon} alt="Sentio Mind" style={{ width: 210, height: 70 }} />
        <div style={{ flex: 1 }} />
        {/* Nav links */}
        {["Dashboard", "Reports", "Alerts", "Settings"].map(t => (
          <button
            key={t}
            className={`sm-nav-link${activeNav === t ? " active" : ""}`}
            onClick={() => setActiveNav(t)}
          >
            {t === "Alerts" && atRisk.length > 0 && (
              <span style={{
                background: C.danger, color: "#fff", borderRadius: 999,
                fontSize: 9, fontWeight: 700, padding: "1px 5px", marginRight: 4,
              }}>{atRisk.length}</span>
            )}
            {t}
          </button>
        ))}

        <div style={{ flex: 1 }} />

        {/* Live pill */}
        <div className="sm-pill sm-pill-live">
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: C.success, flexShrink: 0 }} />
          {persons.length} tracked
        </div>

        {/* Refresh */}
        <button className="sm-icon-btn" onClick={fetchReport} title="Refresh data">
          <RefreshIcon />
        </button>

        {/* User + Logout */}
        <span style={{ fontSize: 13, fontWeight: 500, color: C.charcoal }}>{user?.email || "Counsellor"}</span>
        <LogoutButton variant="counsellor" />
      </nav>

      {/* ── BODY ── */}
      <div className="sm-body">

        {/* Page header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14, flexShrink: 0 }}>
          <div>
            <h1 style={{ fontFamily: "'Poppins',sans-serif", fontSize: 20, fontWeight: 800, color: C.deepTeal, letterSpacing: "-0.03em", lineHeight: 1 }}>
              School Counsellor Dashboard
            </h1>
            <p style={{ fontSize: 11, color: C.muted, marginTop: 3 }}>
              {stats.date_range?.join(" — ")} · {stats.total_dates_analyzed ?? 0} days analysed
            </p>
          </div>
          {/* Search */}
          <div style={{
            display: "flex", alignItems: "center", gap: 8,
            background: "#fff", border: `1px solid ${C.border}`,
            borderRadius: 10, padding: "7px 14px", minWidth: 200,
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={C.muted} strokeWidth="2">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
            </svg>
            <input
              placeholder="Search student…"
              value={searchQuery}
              onChange={e => setSearch(e.target.value)}
              style={{
                border: "none", outline: "none", fontSize: 12,
                color: C.charcoal, background: "transparent",
                fontFamily: "'DM Sans', sans-serif", width: "100%",
              }}
            />
          </div>
        </div>

        {/* KPI row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 10, marginBottom: 14, flexShrink: 0 }}>
          <KpiCard label="Total Students"    value={stats.total_unique_persons ?? persons.length} sub={`${stats.total_schools ?? 1} school(s)`} delay={0} />
          <KpiCard label="Avg Wellbeing"     value={`${avgWb}%`}  sub={wbLabel(avgWb)}        color={wbColor(avgWb)} delay={0.05} />
          <KpiCard label="Avg Engagement"    value={`${avgEng}%`} sub="Across cohort"          color={C.deepTeal}    delay={0.1} />
          <KpiCard label="Days Analysed"     value={stats.total_dates_analyzed ?? 0} sub={stats.date_range?.join(" → ")} delay={0.15} />
          <KpiCard label="Needs Monitoring"  value={atRisk.length} sub="Wellbeing below 50%"  color={atRisk.length > 0 ? C.danger : C.success} delay={0.2} />
        </div>

        {/* Main grid */}
        <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 12, flex: 1, overflow: "hidden", minHeight: 0 }}>

          {/* ── LEFT: Student list + Critical Alerts ── */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10, overflow: "hidden", minHeight: 0 }}>

            {/* Student list */}
            <div className="sm-card sm-reveal" style={{ animationDelay: "0.1s", flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minHeight: 0 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                <div className="sm-card-title" style={{ margin: 0 }}>Students Tracked</div>
                <span style={{ fontSize: 11, color: C.muted }}>{sorted.length} in cohort</span>
              </div>

              {sorted.length === 0 && (
                <div style={{ fontSize: 12, color: C.muted, padding: "10px 0" }}>
                  {searchQuery ? "No students match your search." : "No data yet — run analysis first."}
                </div>
              )}

              <div className="sm-scroll">
                {sorted.map((p, i) => {
                  const isPinned = pinnedIds.includes(p.person_id);
                  const color = wbColor(p.average_wellbeing);
                  const isSelected = selectedPerson?.person_id === p.person_id;
                  return (
                    <div
                      key={p.person_id}
                      className={`sm-person-row${isSelected ? " selected" : ""}`}
                      onClick={() => setSelected(p)}
                      style={{ animationDelay: `${0.15 + i * 0.04}s` }}
                    >
                      <AvatarCircle name={p.name} image={p.profile_image} size={32} color={`linear-gradient(135deg, ${color}cc, ${color}55)`} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: C.charcoal, display: "flex", alignItems: "center", gap: 5 }}>
                          {p.name}
                          {isPinned && (
                            <span style={{ fontSize: 8, color: C.deepTeal, background: "rgba(15,76,92,0.08)", borderRadius: 4, padding: "1px 5px", fontWeight: 700, letterSpacing: "0.06em" }}>PINNED</span>
                          )}
                        </div>
                        <div style={{ fontSize: 10, color: C.muted, marginTop: 1 }}>
                          {p.days_present} day{p.days_present !== 1 ? "s" : ""} present · {p.dominant_gaze} gaze
                        </div>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 2 }}>
                        <span style={{ fontSize: 12, fontWeight: 800, color }}>{p.average_wellbeing}%</span>
                        <div style={{ width: 44, height: 3, background: "#EEF3F6", borderRadius: 2, overflow: "hidden" }}>
                          <div style={{ width: `${p.average_wellbeing}%`, height: "100%", background: color, borderRadius: 2 }} />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Critical Alerts Queue */}
            <div className="sm-card sm-reveal" style={{ animationDelay: "0.18s", flexShrink: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={C.warn} strokeWidth="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
                <span className="sm-card-title" style={{ margin: 0 }}>Critical Alerts Queue</span>
                {atRisk.length > 0 && (
                  <span className="sm-pill sm-pill-danger" style={{ fontSize: 10, padding: "2px 8px", marginLeft: "auto" }}>
                    {atRisk.length} at risk
                  </span>
                )}
              </div>

              {atRisk.length === 0 ? (
                <div style={{ fontSize: 12, color: C.muted }}>No critical alerts — all students above threshold.</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {atRisk.sort((a, b) => a.average_wellbeing - b.average_wellbeing).slice(0, 4).map((p, i) => {
                    const lowest = p.avg_traits
                      ? Object.entries(p.avg_traits).sort((a, b) => a[1] - b[1])[0]
                      : null;
                    return (
                      <div
                        key={p.person_id}
                        style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}
                        onClick={() => setSelected(p)}
                      >
                        <AvatarCircle name={p.name} image={p.profile_image} size={34}
                          color={`linear-gradient(135deg, ${C.danger}88, ${C.danger}44)`} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: C.charcoal }}>{p.name}</div>
                          {lowest && (
                            <div style={{ fontSize: 10, color: C.muted }}>
                              Lowest: {lowest[0].replace(/_/g, " ")} ({lowest[1]}%)
                            </div>
                          )}
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: C.danger, fontWeight: 600 }}>
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={C.danger} strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                            <line x1="12" y1="8" x2="12" y2="12" />
                            <line x1="12" y1="16" x2="12.01" y2="16" />
                          </svg>
                          Intervene
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* ── RIGHT: Detail panel ── */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10, overflow: "hidden", minHeight: 0 }}>

            {/* Student detail header + sparkline */}
            <div className="sm-card sm-reveal" style={{ animationDelay: "0.22s", flexShrink: 0 }}>
              {selectedPerson ? (
                <>
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 12 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <AvatarCircle name={selectedPerson.name} image={selectedPerson.profile_image} size={44}
                        color={`linear-gradient(135deg, ${wbColor(selectedPerson.average_wellbeing)}, ${wbColor(selectedPerson.average_wellbeing)}88)`} />
                      <div>
                        <div style={{ fontFamily: "'Poppins',sans-serif", fontWeight: 700, fontSize: 16, color: C.deepTeal }}>
                          {selectedPerson.name}
                        </div>
                        <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>
                          {selectedPerson.days_present} day{selectedPerson.days_present !== 1 ? "s" : ""} present ·
                          Dominant gaze: {selectedPerson.dominant_gaze} ·
                          Last seen: {selectedPerson.dates_seen?.at(-1) ?? "—"}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div className="sm-pill" style={{ background: `${wbColor(selectedPerson.average_wellbeing)}18`, color: wbColor(selectedPerson.average_wellbeing) }}>
                        Wellbeing {selectedPerson.average_wellbeing}%
                      </div>
                      <div className="sm-pill sm-pill-info">
                        Engagement {selectedPerson.average_engagement}%
                      </div>
                      <div className="sm-pill" style={{ background: "#F0F4F7", color: C.muted }}>
                        {wbLabel(selectedPerson.average_wellbeing)}
                      </div>
                    </div>
                  </div>
                  <SparklineCanvas student={selectedPerson} />
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, padding: "0 6px" }}>
                    {Object.keys(selectedPerson.avg_traits || {}).slice(0, 5).map(k => (
                      <span key={k} style={{ fontSize: 9, color: C.muted }}>
                        {k.replace(/_/g, " ").split(" ").slice(0, 2).join(" ")}
                      </span>
                    ))}
                  </div>
                </>
              ) : (
                <div style={{ fontSize: 12, color: C.muted, padding: "20px 0", textAlign: "center" }}>
                  Select a student from the list to view their profile
                </div>
              )}
            </div>

            {/* Tabs + Trait breakdown */}
            <div className="sm-card sm-reveal" style={{ animationDelay: "0.26s", flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minHeight: 0 }}>
              {/* Tabs */}
              <div style={{ display: "flex", gap: 20, borderBottom: `1px solid ${C.border}`, marginBottom: 14, flexShrink: 0 }}>
                {["Overview", "Traits", "History"].map(tab => (
                  <button
                    key={tab}
                    className={`sm-tab${activeTab === tab ? " active" : ""}`}
                    onClick={() => setActiveTab(tab)}
                  >
                    {tab}
                  </button>
                ))}
                {selectedPerson && (
                  <span style={{ marginLeft: "auto", fontSize: 11, color: C.muted, alignSelf: "center" }}>
                    {selectedPerson.name}
                  </span>
                )}
              </div>

              {selectedPerson ? (
                <div style={{ display: "flex", gap: 16, flex: 1, overflow: "hidden", minHeight: 0 }}>
                  {/* Trait bars */}
                  <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minHeight: 0 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: C.muted, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10, flexShrink: 0 }}>
                      Trait Breakdown
                    </div>
                    <div className="sm-scroll">
                      {Object.entries(selectedPerson.avg_traits || {}).map(([k, v]) => (
                        <TraitBar key={k} label={k.replace(/_/g, " ")} value={v} />
                      ))}
                    </div>

                    {/* Low trait risk panel */}
                    {lowTraits.length > 0 && (
                      <div className="sm-risk-panel">
                        <div className="sm-risk-label">Low Trait Flags ({lowTraits.length})</div>
                        {lowTraits.map(([k, v]) => (
                          <div key={k} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 12, marginBottom: 5 }}>
                            <span style={{ color: C.charcoal }}>{k.replace(/_/g, " ")}</span>
                            <span style={{ fontWeight: 800, color: C.danger }}>{v}%</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Right: Heat grid + meta */}
                  <div style={{ width: 220, display: "flex", flexDirection: "column", gap: 10, flexShrink: 0 }}>
                    {/* Weekly heat */}
                    <div style={{ background: "#F7F9FB", borderRadius: 12, padding: "12px 14px" }}>
                      <div style={{ fontSize: 10, fontWeight: 600, color: C.muted, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
                        Weekly Behaviour Heat
                      </div>
                      <HeatGrid persons={[selectedPerson]} />
                      <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
                        {[
                          { color: C.deepTeal, label: "High" },
                          { color: C.aquaTeal, label: "Med-Hi" },
                          { color: C.softBlue, label: "Medium" },
                          { color: "#B8DDE8", label: "Low" },
                        ].map(({ color, label }) => (
                          <div key={label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                            <div style={{ width: 8, height: 8, borderRadius: 2, background: color }} />
                            <span style={{ fontSize: 9, color: C.muted }}>{label}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Meta card */}
                    <div style={{ background: "#F7F9FB", borderRadius: 12, padding: "12px 14px", flex: 1 }}>
                      <div style={{ fontSize: 10, fontWeight: 600, color: C.muted, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
                        Profile Info
                      </div>
                      {[
                        { label: "Person ID",    value: selectedPerson.person_id },
                        { label: "Days Present", value: selectedPerson.days_present },
                        { label: "Dominant Gaze", value: selectedPerson.dominant_gaze },
                        { label: "Pinned",       value: pinnedIds.includes(selectedPerson.person_id) ? "Yes" : "No" },
                        { label: "Last Seen",    value: selectedPerson.dates_seen?.at(-1) ?? "—" },
                        { label: "Total Detections", value: selectedPerson.total_detections ?? "—" },
                      ].map(({ label, value }) => (
                        <div key={label} style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 7 }}>
                          <span style={{ color: C.muted }}>{label}</span>
                          <span style={{ fontWeight: 600, color: C.charcoal, maxWidth: 110, textAlign: "right", wordBreak: "break-all" }}>{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: C.muted, fontSize: 13 }}>
                  No student selected
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}