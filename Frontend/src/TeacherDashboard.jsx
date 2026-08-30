import { useState, useEffect } from "react";
import LogoutButton from "./components/LogoutButton";
import { useSession } from "./context/SessionContext";
import {
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Area, AreaChart,
} from "recharts";
import icon from "./assets/icon.png";
import { API_BASE } from "./config/env";
import { authFetch } from "./services/authApi";

// ─── Brand tokens (mirrors PrincipalDashboard exactly) ────────────────────────
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

// ─── Global CSS (same architecture as Principal) ──────────────────────────────
const GLOBAL_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800&family=DM+Sans:wght@300;400;500;600&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  .sm-t {
    font-family: 'DM Sans', sans-serif;
    background: ${C.offWhite};
    color: ${C.charcoal};
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .sm-t ::-webkit-scrollbar { width: 5px; }
  .sm-t ::-webkit-scrollbar-track { background: #e0f2fe; }
  .sm-t ::-webkit-scrollbar-thumb { background: ${C.aquaTeal}; border-radius: 3px; }

  /* ── Navbar ── */
  .sm-t-nav {
    background: rgba(247,249,251,0.88);
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

  .sm-t-nav-logo {
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

  .sm-t-nav-sub {
    font-size: 9px;
    color: ${C.muted};
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 1px;
  }

  .sm-t-nav-link {
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
  }
  .sm-t-nav-link:hover { color: ${C.deepTeal}; }
  .sm-t-nav-link.active {
    color: ${C.deepTeal};
    font-weight: 700;
    border-bottom-color: ${C.aquaTeal};
  }

  /* ── Layout ── */
  .sm-t-body {
    flex: 1;
    overflow: hidden;
    display: flex;
    min-height: 0;
  }

  /* ── Sidebar ── */
  .sm-t-sidebar {
    width: 248px;
    background: #fff;
    border-right: 1px solid ${C.border};
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    overflow: hidden;
  }

  .sm-t-sidebar-head {
    padding: 18px 18px 12px;
    border-bottom: 1px solid ${C.border};
    flex-shrink: 0;
  }

  .sm-t-sidebar-label {
    font-size: 9px;
    font-weight: 700;
    color: ${C.muted};
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .sm-t-search {
    display: flex;
    align-items: center;
    gap: 7px;
    border: 1px solid ${C.border};
    border-radius: 8px;
    padding: 6px 10px;
    background: ${C.offWhite};
    transition: border-color 0.2s;
  }
  .sm-t-search:focus-within {
    border-color: ${C.aquaTeal};
    background: #fff;
  }
  .sm-t-search input {
    border: none;
    outline: none;
    font-family: 'DM Sans', sans-serif;
    font-size: 12px;
    background: transparent;
    color: ${C.charcoal};
    width: 100%;
  }
  .sm-t-search input::placeholder { color: ${C.muted}; }

  .sm-t-student-list {
    flex: 1;
    overflow-y: auto;
    padding: 10px 12px;
  }

  .sm-t-student-row {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 8px 10px;
    border-radius: 9px;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
    border: 1.5px solid transparent;
    margin-bottom: 2px;
  }
  .sm-t-student-row:hover { background: #F0FAF9; }
  .sm-t-student-row.selected {
    background: rgba(46,196,182,0.07);
    border-color: ${C.border};
  }

  /* ── Main content ── */
  .sm-t-main {
    flex: 1;
    overflow-y: auto;
    padding: 20px 24px;
    min-height: 0;
  }

  /* ── Cards ── */
  .sm-t-card {
    background: #fff;
    border: 1px solid ${C.border};
    border-radius: 14px;
    padding: 18px 20px;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .sm-t-card:hover {
    border-color: ${C.borderHover};
    box-shadow: 0 4px 20px rgba(15,76,92,0.06);
  }

  .sm-t-card-title {
    font-family: 'Poppins', sans-serif;
    font-size: 12px;
    font-weight: 700;
    color: ${C.deepTeal};
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 14px;
  }

  /* ── KPI tiles ── */
  .sm-t-kpi {
    background: #fff;
    border: 1px solid ${C.border};
    border-radius: 12px;
    padding: 14px 18px;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .sm-t-kpi:hover {
    border-color: ${C.borderHover};
    box-shadow: 0 3px 14px rgba(15,76,92,0.07);
  }
  .sm-t-kpi-label {
    font-size: 9px;
    font-weight: 700;
    color: ${C.muted};
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 5px;
  }
  .sm-t-kpi-val {
    font-family: 'Poppins', sans-serif;
    font-size: 24px;
    font-weight: 800;
    line-height: 1;
    color: ${C.deepTeal};
  }
  .sm-t-kpi-sub { font-size: 10px; color: ${C.muted}; margin-top: 3px; }

  /* ── Trait bars ── */
  .sm-t-bar-track {
    width: 100%;
    height: 4px;
    background: #EEF3F6;
    border-radius: 2px;
    overflow: hidden;
  }
  .sm-t-bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.55s cubic-bezier(0.16,1,0.3,1);
  }

  /* ── Status pill ── */
  .sm-t-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    border-radius: 100px;
    padding: 3px 10px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.04em;
  }
  .sm-t-pill-live { background: rgba(42,140,114,0.10); color: ${C.success}; }
  .sm-t-pill-warn { background: rgba(196,122,46,0.10); color: ${C.warn}; }
  .sm-t-pill-info { background: rgba(111,190,220,0.15); color: ${C.deepTeal}; }

  /* ── Icon btn ── */
  .sm-t-icon-btn {
    width: 32px; height: 32px;
    border: 1px solid ${C.border};
    border-radius: 8px;
    background: #fff;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: border-color 0.2s, background 0.2s;
    color: ${C.muted};
  }
  .sm-t-icon-btn:hover { border-color: ${C.aquaTeal}; background: rgba(46,196,182,0.05); color: ${C.deepTeal}; }

  /* ── Highlight panel ── */
  .sm-t-highlight {
    background: rgba(42,140,114,0.05);
    border: 1px solid rgba(42,140,114,0.18);
    border-radius: 10px;
    padding: 12px 14px;
  }

  /* ── Reveal animation ── */
  @keyframes smTFadeUp {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .sm-t-reveal { animation: smTFadeUp 0.5s cubic-bezier(0.16,1,0.3,1) both; }

  @keyframes smTSpin { to { transform: rotate(360deg); } }

  /* ── Distribution tiles ── */
  .sm-t-dist-tile {
    border-radius: 12px;
    padding: 16px 18px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
`;

// ─── Helpers ──────────────────────────────────────────────────────────────────
function wbColor(v) {
  if (v >= 70) return C.success;
  if (v >= 55) return C.aquaTeal;
  if (v >= 40) return C.warn;
  return C.danger;
}

function wbLabel(v) {
  if (v >= 70) return "Flourishing";
  if (v >= 55) return "Needs Monitoring";
  if (v >= 40) return "Support Recommended";
  return "Immediate Attention";
}

function barColor(v) {
  if (v >= 70) return C.success;
  if (v >= 45) return C.aquaTeal;
  return C.warn;
}

function avgClassWellbeing(persons) {
  if (!persons.length) return 0;
  return Math.round(persons.reduce((a, p) => a + p.average_wellbeing, 0) / persons.length);
}

function buildDistribution(persons) {
  let flourishing = 0, monitoring = 0, support = 0, attention = 0;
  persons.forEach(p => {
    const s = p.average_wellbeing;
    if (s >= 70) flourishing++;
    else if (s >= 55) monitoring++;
    else if (s >= 40) support++;
    else attention++;
  });
  return { flourishing, monitoring, support, attention };
}

function buildChartData(persons) {
  const allPoints = [];
  persons.forEach(p => (p.temporal_series || []).forEach(pt => allPoints.push(pt)));
  if (!allPoints.length) return [];
  allPoints.sort((a, b) => a.date.localeCompare(b.date));
  const dates = [...new Set(allPoints.map(p => p.date))].sort();
  const labels = ["Week 1", "Week 2", "Week 4", "30 Days"];
  return dates.slice(-4).map((date, i) => {
    const pts = allPoints.filter(p => p.date === date);
    const avgWell = pts.length ? Math.round(pts.reduce((a, v) => a + v.wellbeing, 0) / pts.length) : 50;
    return { week: labels[i] || date, positive: avgWell, neutral: Math.round(avgWell * 0.6) };
  });
}

function topPerformers(persons) {
  return [...persons].sort((a, b) => b.average_wellbeing - a.average_wellbeing).slice(0, 3);
}

// ─── Sub-components ───────────────────────────────────────────────────────────
function AvatarCircle({ name, image, size = 32 }) {
  if (image) return (
    <img src={`data:image/jpeg;base64,${image}`} alt={name}
      style={{ width: size, height: size, borderRadius: "50%", objectFit: "cover", flexShrink: 0 }} />
  );
  const initials = (name || "?").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  return (
    <div style={{
      width: size, height: size, borderRadius: "50%", flexShrink: 0,
      background: `linear-gradient(135deg, ${C.deepTeal}, ${C.aquaTeal})`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: size > 28 ? 11 : 10, fontWeight: 700, color: "#fff", letterSpacing: "0.03em",
    }}>{initials}</div>
  );
}

function TraitBar({ label, value }) {
  const color = barColor(value);
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: C.muted, fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: 11, fontWeight: 700, color }}>{value}%</span>
      </div>
      <div className="sm-t-bar-track">
        <div className="sm-t-bar-fill" style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  );
}

function RefreshIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

function PrintIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 6 2 18 2 18 9" />
      <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
      <rect x="6" y="14" width="12" height="8" />
    </svg>
  );
}

function SearchIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={C.muted} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function TrophyIcon({ color = C.warn }) {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="8 15 3 15 3 3 21 3 21 15 16 15" />
      <path d="M15.73 15C14.6 18.72 12 21 12 21s-2.6-2.28-3.73-6" />
      <line x1="12" y1="21" x2="12" y2="15" /><line x1="9" y1="21" x2="15" y2="21" />
    </svg>
  );
}

function CheckIcon({ color = C.success }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}

function TrendUpIcon({ color = C.success }) {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" />
    </svg>
  );
}

function TrendDownIcon({ color = C.danger }) {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" /><polyline points="17 18 23 18 23 12" />
    </svg>
  );
}

// ─── Custom chart dot ─────────────────────────────────────────────────────────
const CustomDot = (props) => {
  const { cx, cy, stroke, index, dataLength } = props;
  if (index === 1 || index === 2) return <circle cx={cx} cy={cy} r={5} stroke={stroke} strokeWidth={2} fill="white" />;
  if (index === dataLength - 1) return <circle cx={cx} cy={cy} r={6} stroke={stroke} strokeWidth={2.5} fill="white" />;
  return null;
};

// ─── Main Component ───────────────────────────────────────────────────────────
export default function TeacherDashboard() {
  const { user } = useSession();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPersonId, setSelectedPersonId] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeNav, setActiveNav] = useState("Reports");

  useEffect(() => { fetchReport(); }, []);

  async function fetchReport() {
    setLoading(true);
    setError(null);
    try {
      const data = await authFetch("/analysis/report");
      if (data.success && data.report) {
        setReport(data.report);
        const persons = Object.values(data.report.person_profiles || {});
        if (persons.length) setSelectedPersonId(persons[0].person_id);
      } else {
        setError("No report available. Run the analysis first.");
      }
    } catch {
      setError("Cannot connect to backend at " + API_BASE);
    }
    setLoading(false);
  }

  // ── Derived data ─────────────────────────────────────────────────────────────
  const allPersons = report ? Object.values(report.person_profiles || {}) : [];
  const filteredPersons = allPersons.filter(p =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );
  const selectedPerson = allPersons.find(p => p.person_id === selectedPersonId) || allPersons[0] || null;
  const classWellbeing = avgClassWellbeing(allPersons);
  const distribution = buildDistribution(allPersons);
  const chartData = buildChartData(allPersons);
  const performers = topPerformers(allPersons);
  const atRisk = allPersons.filter(p => p.average_wellbeing < 50);
  const stats = report?.overall_stats || {};

  const classTrend = classWellbeing >= 70
    ? { icon: <TrendUpIcon />, label: "Stable", color: C.success }
    : classWellbeing >= 50
      ? { icon: <span style={{ fontSize: 11, color: C.warn }}>—</span>, label: "Moderate", color: C.warn }
      : { icon: <TrendDownIcon />, label: "Declining", color: C.danger };

  // ── Loading ───────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="sm-t" style={{ alignItems: "center", justifyContent: "center", gap: 14 }}>
        <style>{GLOBAL_CSS}</style>
        <div style={{
          width: 30, height: 30,
          border: `2.5px solid #EEF3F6`,
          borderTopColor: C.aquaTeal,
          borderRadius: "50%",
          animation: "smTSpin 0.7s linear infinite",
        }} />
        <span style={{ fontSize: 13, color: C.muted }}>Loading class data…</span>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="sm-t" style={{ alignItems: "center", justifyContent: "center", gap: 12, padding: 40 }}>
        <style>{GLOBAL_CSS}</style>
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke={C.warn} strokeWidth="1.5">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <div style={{ fontFamily: "'Poppins',sans-serif", fontSize: 15, fontWeight: 700, color: C.deepTeal }}>
          Connection Error
        </div>
        <div style={{ fontSize: 13, color: C.muted, textAlign: "center", maxWidth: 360 }}>{error}</div>
        <button onClick={fetchReport} style={{
          marginTop: 8, padding: "9px 22px",
          background: `linear-gradient(135deg, ${C.deepTeal}, ${C.aquaTeal})`,
          color: "#fff", border: "none", borderRadius: 9,
          fontSize: 13, fontWeight: 600, cursor: "pointer",
        }}>
          Retry
        </button>
      </div>
    );
  }

  if (!allPersons.length) {
    return (
      <div className="sm-t" style={{ alignItems: "center", justifyContent: "center", gap: 10 }}>
        <style>{GLOBAL_CSS}</style>
        <UsersIcon />
        <div style={{ fontFamily: "'Poppins',sans-serif", fontSize: 15, fontWeight: 700, color: C.deepTeal }}>
          No analysis data yet
        </div>
        <div style={{ fontSize: 13, color: C.muted }}>Run the analysis pipeline first, then return here.</div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="sm-t">
      <style>{GLOBAL_CSS}</style>

      {/* ── NAVBAR ── */}
      <nav className="sm-t-nav">
        {/* Logo */}
        <img src={icon} alt="Sentio Mind" style={{ width: 210, height: 70 }} />

        {/* Nav links */}
        {["Reports", "Alerts", "Settings"].map(t => (
          <button key={t} className={`sm-t-nav-link${activeNav === t ? " active" : ""}`}
            onClick={() => setActiveNav(t)} style={{ position: "relative" }}>
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

        {/* Pill */}
        <div className="sm-t-pill sm-t-pill-live">
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: C.success, flexShrink: 0 }} />
          {allPersons.length} students
        </div>

        {/* Actions */}
        <button className="sm-t-icon-btn" onClick={() => window.print()} title="Print">
          <PrintIcon />
        </button>
        <button className="sm-t-icon-btn" onClick={fetchReport} title="Refresh">
          <RefreshIcon />
        </button>

        <span style={{ fontSize: 13, fontWeight: 500, color: C.charcoal }}>{user?.email || "Teacher"}</span>
        <LogoutButton />
      </nav>

      {/* ── BODY ── */}
      <div className="sm-t-body">

        {/* ── SIDEBAR ── */}
        <aside className="sm-t-sidebar">
          <div className="sm-t-sidebar-head">
            <div className="sm-t-sidebar-label">
              <UsersIcon />
              Student Profiles
            </div>
            <div className="sm-t-search">
              <SearchIcon size={13} />
              <input
                type="text"
                placeholder="Search students…"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          <div className="sm-t-student-list">
            {filteredPersons.slice(0, 8).map(person => {
              const color = wbColor(person.average_wellbeing);
              const isSelected = selectedPersonId === person.person_id;
              return (
                <div
                  key={person.person_id}
                  className={`sm-t-student-row${isSelected ? " selected" : ""}`}
                  onClick={() => setSelectedPersonId(person.person_id)}
                >
                  <AvatarCircle name={person.name} image={person.profile_image} size={34} />
                  <span style={{ flex: 1, fontSize: 13, fontWeight: 500, color: C.charcoal }}>{person.name}</span>
                  {isSelected
                    ? <CheckIcon />
                    : person.average_wellbeing >= 70
                      ? <CheckIcon color={C.success} />
                      : <span style={{ fontSize: 11, color, fontWeight: 700 }}>{person.average_wellbeing}%</span>
                  }
                </div>
              );
            })}
            {filteredPersons.length === 0 && (
              <div style={{ fontSize: 12, color: C.muted, padding: "14px 0", textAlign: "center" }}>
                No students found
              </div>
            )}
          </div>

          {/* Positive highlights */}
          {performers.length > 0 && (
            <div style={{ padding: "0 12px 16px", flexShrink: 0, borderTop: `1px solid ${C.border}` }}>
              <div style={{
                fontSize: 9, fontWeight: 700, color: C.muted,
                letterSpacing: "0.1em", textTransform: "uppercase",
                margin: "12px 0 8px",
                display: "flex", alignItems: "center", gap: 5,
              }}>
                <TrophyIcon color={C.warn} />
                Positive Highlights
              </div>
              {performers.map((p, i) => (
                <div key={p.person_id} style={{
                  display: "flex", alignItems: "flex-start", gap: 7, marginBottom: 8,
                }}>
                  <AvatarCircle name={p.name} image={p.profile_image} size={26} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: C.charcoal }}>{p.name}</div>
                    <div style={{ fontSize: 10, color: C.muted, marginTop: 1 }}>
                      {p.average_wellbeing}% wellbeing
                      {i === 0 ? " · top performer" : ""}
                    </div>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 800, color: wbColor(p.average_wellbeing), marginLeft: "auto", flexShrink: 0 }}>
                    {p.average_wellbeing}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </aside>

        {/* ── MAIN CONTENT ── */}
        <main className="sm-t-main">

          {/* Page header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <div>
              <h1 style={{
                fontFamily: "'Poppins',sans-serif", fontSize: 20, fontWeight: 800,
                color: C.deepTeal, letterSpacing: "-0.03em", lineHeight: 1,
              }}>
                Class Teacher Dashboard
              </h1>
              <p style={{ fontSize: 11, color: C.muted, marginTop: 3 }}>
                {stats.date_range?.join(" — ")} · {stats.total_dates_analyzed || 0} days analysed
              </p>
            </div>
            <div className="sm-t-pill sm-t-pill-info" style={{ fontSize: 11 }}>
              {stats.total_unique_persons || 0} students tracked
            </div>
          </div>

          {/* ── KPI ROW ── */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 16 }}
            className="sm-t-reveal">
            <div className="sm-t-kpi" style={{ animationDelay: "0s" }}>
              <div className="sm-t-kpi-label">Class Wellbeing</div>
              <div className="sm-t-kpi-val" style={{ color: wbColor(classWellbeing) }}>{classWellbeing}%</div>
              <div className="sm-t-kpi-sub" style={{ display: "flex", alignItems: "center", gap: 4 }}>
                {classTrend.icon}
                <span style={{ color: classTrend.color }}>{classTrend.label}</span>
              </div>
            </div>
            <div className="sm-t-kpi" style={{ animationDelay: "0.05s" }}>
              <div className="sm-t-kpi-label">Flourishing</div>
              <div className="sm-t-kpi-val" style={{ color: C.success }}>{distribution.flourishing}</div>
              <div className="sm-t-kpi-sub">Wellbeing ≥ 70%</div>
            </div>
            <div className="sm-t-kpi" style={{ animationDelay: "0.1s" }}>
              <div className="sm-t-kpi-label">Need Support</div>
              <div className="sm-t-kpi-val" style={{ color: distribution.support + distribution.attention > 0 ? C.warn : C.deepTeal }}>
                {distribution.support + distribution.attention}
              </div>
              <div className="sm-t-kpi-sub">Below threshold</div>
            </div>
            <div className="sm-t-kpi" style={{ animationDelay: "0.15s" }}>
              <div className="sm-t-kpi-label">Immediate Attention</div>
              <div className="sm-t-kpi-val" style={{ color: distribution.attention > 0 ? C.danger : C.success }}>
                {distribution.attention}
              </div>
              <div className="sm-t-kpi-sub">Wellbeing &lt; 40%</div>
            </div>
          </div>

          {/* ── TWO COLUMN GRID ── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>

            {/* Wellbeing Distribution */}
            <div className="sm-t-card sm-t-reveal" style={{ animationDelay: "0.18s" }}>
              <div className="sm-t-card-title">Wellbeing Distribution</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                {[
                  { label: "Flourishing", val: distribution.flourishing, bg: "rgba(42,140,114,0.08)", border: "rgba(42,140,114,0.20)", color: C.success },
                  { label: "Needs Monitoring", val: distribution.monitoring, bg: "rgba(196,122,46,0.07)", border: "rgba(196,122,46,0.20)", color: C.warn },
                  { label: "Support Recommended", val: distribution.support, bg: "rgba(208,101,60,0.07)", border: "rgba(208,101,60,0.20)", color: "#D0654A" },
                  { label: "Immediate Attention", val: distribution.attention, bg: "rgba(208,69,76,0.07)", border: "rgba(208,69,76,0.20)", color: C.danger },
                ].map(({ label, val, bg, border, color }) => (
                  <div key={label} className="sm-t-dist-tile"
                    style={{ background: bg, border: `1px solid ${border}` }}>
                    <div style={{ fontSize: 9, fontWeight: 700, color, letterSpacing: "0.07em", textTransform: "uppercase" }}>
                      {label}
                    </div>
                    <div style={{
                      fontFamily: "'Poppins',sans-serif",
                      fontSize: 28, fontWeight: 800, lineHeight: 1.1, color,
                    }}>{val}</div>
                    <div style={{ fontSize: 9, color, opacity: 0.7 }}>
                      {allPersons.length ? Math.round(val / allPersons.length * 100) : 0}% of class
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Wellbeing trend chart */}
            {chartData.length > 0 && (
              <div className="sm-t-card sm-t-reveal" style={{ animationDelay: "0.22s" }}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 8 }}>
                  <div className="sm-t-card-title" style={{ margin: 0 }}>Wellbeing Trend — 30 Days</div>
                  <div style={{ display: "flex", gap: 12, fontSize: 10, color: C.muted }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: C.aquaTeal, display: "inline-block" }} />
                      Avg wellbeing
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: C.warn, display: "inline-block" }} />
                      Baseline
                    </span>
                  </div>
                </div>
                <div style={{ height: 170 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="tcGrad1" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={C.aquaTeal} stopOpacity={0.15} />
                          <stop offset="95%" stopColor={C.aquaTeal} stopOpacity={0.01} />
                        </linearGradient>
                        <linearGradient id="tcGrad2" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={C.warn} stopOpacity={0.10} />
                          <stop offset="95%" stopColor={C.warn} stopOpacity={0.01} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid vertical={false} stroke="#EEF3F6" strokeDasharray="4 4" />
                      <XAxis dataKey="week" tick={{ fontSize: 10, fill: C.muted }} axisLine={false} tickLine={false} />
                      <YAxis tickFormatter={v => `${v}%`} tick={{ fontSize: 10, fill: C.muted }} axisLine={false} tickLine={false} domain={[0, 100]} />
                      <Tooltip
                        contentStyle={{ borderRadius: 8, border: `1px solid ${C.border}`, fontSize: 12, fontFamily: "'DM Sans',sans-serif" }}
                        formatter={(v, name) => [`${v}%`, name === "positive" ? "Avg Wellbeing" : "Baseline"]}
                      />
                      <Area type="monotone" dataKey="neutral" stroke={C.warn} strokeWidth={2}
                        fill="url(#tcGrad2)"
                        dot={p => <CustomDot {...p} dataLength={chartData.length} />}
                        activeDot={{ r: 5, fill: C.warn }} />
                      <Area type="monotone" dataKey="positive" stroke={C.aquaTeal} strokeWidth={2.5}
                        fill="url(#tcGrad1)"
                        dot={p => <CustomDot {...p} dataLength={chartData.length} />}
                        activeDot={{ r: 5, fill: C.aquaTeal }} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>

          {/* ── STUDENT DETAIL ── */}
          {selectedPerson && (
            <div className="sm-t-card sm-t-reveal" style={{ animationDelay: "0.26s", marginBottom: 12 }}>
              {/* Header */}
              <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 18, paddingBottom: 14, borderBottom: `1px solid ${C.border}` }}>
                <AvatarCircle name={selectedPerson.name} image={selectedPerson.profile_image} size={48} />
                <div style={{ flex: 1 }}>
                  <h2 style={{ fontFamily: "'Poppins',sans-serif", fontSize: 15, fontWeight: 700, color: C.deepTeal, margin: 0 }}>
                    {selectedPerson.name}
                  </h2>
                  <div style={{ fontSize: 11, color: C.muted, marginTop: 3 }}>
                    {selectedPerson.school} · {selectedPerson.person_id} · {selectedPerson.total_detections} detections · {selectedPerson.days_present} days
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{
                    fontFamily: "'Poppins',sans-serif",
                    fontSize: 28, fontWeight: 800,
                    color: wbColor(selectedPerson.average_wellbeing), lineHeight: 1,
                  }}>
                    {selectedPerson.average_wellbeing}%
                  </div>
                  <div style={{ fontSize: 10, color: C.muted, marginTop: 3 }}>
                    {wbLabel(selectedPerson.average_wellbeing)}
                  </div>
                </div>
              </div>

              {/* Trait bars — 2 col */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 24px" }}>
                {selectedPerson.avg_traits && Object.entries({
                  emotional_positivity: "Emotional Positivity",
                  stress_resilience: "Stress Resilience",
                  social_engagement: "Social Engagement",
                  social_confidence: "Social Confidence",
                  physical_energy: "Physical Energy",
                  posture_health: "Posture Health",
                  body_openness: "Body Openness",
                  focus_alertness: "Focus & Alertness",
                  facial_relaxation: "Facial Relaxation",
                  vitality_glow: "Vitality & Glow",
                }).map(([key, label]) => {
                  const val = selectedPerson.avg_traits[key] ?? 50;
                  return <TraitBar key={key} label={label} value={val} />;
                })}
              </div>

              {/* Meta row */}
              {selectedPerson.dominant_gaze && (
                <div style={{
                  marginTop: 14, padding: "10px 14px",
                  background: C.offWhite, borderRadius: 8,
                  border: `1px solid ${C.border}`,
                  display: "flex", gap: 20, flexWrap: "wrap",
                }}>
                  {[
                    ["Dominant Gaze", selectedPerson.dominant_gaze],
                    ["Avg Engagement", `${selectedPerson.average_engagement}%`],
                    ["First Seen", selectedPerson.dates_seen?.[0] || "—"],
                    ["Last Seen", selectedPerson.dates_seen?.at(-1) || "—"],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <span style={{ fontSize: 10, color: C.muted }}>{k}: </span>
                      <span style={{ fontSize: 11, fontWeight: 600, color: C.charcoal }}>{v}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── POSITIVE HIGHLIGHTS (full width) ── */}
          {performers.length > 0 && (
            <div className="sm-t-card sm-t-reveal" style={{ animationDelay: "0.30s" }}>
              <div className="sm-t-card-title">Positive Highlights</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {performers.map((p, i) => {
                  const topTrait = p.avg_traits
                    ? Object.entries(p.avg_traits).sort((a, b) => b[1] - a[1])[0]
                    : null;
                  const colors = [C.success, C.aquaTeal, C.warn];
                  const color = colors[i] || C.muted;
                  return (
                    <div key={p.person_id} style={{
                      display: "flex", alignItems: "center", gap: 10,
                      padding: "10px 12px",
                      background: i === 0 ? "rgba(42,140,114,0.04)" : "transparent",
                      border: `1px solid ${i === 0 ? "rgba(42,140,114,0.14)" : C.border}`,
                      borderRadius: 9,
                    }}>
                      <AvatarCircle name={p.name} image={p.profile_image} size={32} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: C.charcoal }}>{p.name}</div>
                        <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>
                          {topTrait
                            ? `${topTrait[0].replace(/_/g, " ")} at ${topTrait[1]}% — above class average`
                            : `Wellbeing ${p.average_wellbeing}% — flourishing overall`}
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        {i === 0 && <TrophyIcon color={C.warn} />}
                        <span style={{
                          fontFamily: "'Poppins',sans-serif",
                          fontSize: 15, fontWeight: 800, color,
                        }}>{p.average_wellbeing}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}