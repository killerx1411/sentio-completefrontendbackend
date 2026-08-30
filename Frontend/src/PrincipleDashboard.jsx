/**
 * Sentio Mind — Principal Dashboard
 * Brand palette: Deep Teal #0F4C5C · Aqua Teal #2EC4B6 · Soft Blue #6FBEDC
 *                Off White #F7F9FB · Charcoal Grey #3A3F45
 * Typography   : Poppins (headings) · DM Sans (body) · no Inter/Roboto slop
 * Style        : matches SentioMind landing page exactly
 */

import { useState, useEffect, useRef } from "react";
import LogoutButton from "./components/LogoutButton";
import { useSession } from "./context/SessionContext";
import icon from "./assets/icon.png";
// ─── Backend routing (from Code 1) ───────────────────────────────────────────
import { authFetch } from "./services/authApi";

// ─── Brand tokens ────────────────────────────────────────────────────────────
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

// ─── Injected CSS (mirrors landing page globalStyle) ─────────────────────────
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

  /* ── Scrollbars ── */
  .sm-dash ::-webkit-scrollbar { width: 5px; }
  .sm-dash ::-webkit-scrollbar-track { background: #e0f2fe; }
  .sm-dash ::-webkit-scrollbar-thumb { background: ${C.aquaTeal}; border-radius: 3px; }

  /* ── Navbar ── */
  .sm-nav {
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
  }
  .sm-nav-link:hover { color: ${C.deepTeal}; }
  .sm-nav-link.active {
    color: ${C.deepTeal};
    font-weight: 700;
    border-bottom-color: ${C.aquaTeal};
  }

  /* ── Page body ── */
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
  .sm-trait-row { margin-bottom: 8px; }
  .sm-trait-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
  }
  .sm-trait-name { font-size: 11px; color: ${C.muted}; font-weight: 500; }
  .sm-trait-pct  { font-size: 11px; font-weight: 700; }
  .sm-bar-track  { width: 100%; height: 4px; background: #EEF3F6; border-radius: 2px; overflow: hidden; }
  .sm-bar-fill   { height: 100%; border-radius: 2px; transition: width 0.6s cubic-bezier(0.16,1,0.3,1); }

  /* ── Heat grid ── */
  .sm-heat-cell {
    flex: 1;
    height: 26px;
    border-radius: 5px;
    transition: opacity 0.2s;
  }
  .sm-heat-cell:hover { opacity: 0.75; }

  /* ── Person row ── */
  .sm-person-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-top: 1px solid #F0F4F7;
    transition: background 0.15s;
    border-radius: 6px;
    cursor: default;
  }
  .sm-person-row:hover { background: #F7FDFC; }

  /* ── Climate cell ── */
  .sm-climate-cell {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 700;
    color: rgba(255,255,255,0.9);
    cursor: pointer;
    border-right: 1px solid rgba(255,255,255,0.12);
    transition: filter 0.2s;
  }
  .sm-climate-cell:last-child { border-right: none; }
  .sm-climate-cell:hover { filter: brightness(1.1); }

  /* ── Trend row ── */
  .sm-trend-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
  }

  /* ── At-risk panel ── */
  .sm-risk-panel {
    background: #FEF7F7;
    border: 1px solid rgba(208,69,76,0.2);
    border-radius: 10px;
    padding: 12px 14px;
    margin-top: 12px;
  }
  .sm-risk-label {
    font-size: 10px;
    font-weight: 700;
    color: ${C.danger};
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  /* ── Tab button ── */
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

  /* ── Status pill ── */
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
  .sm-pill-live { background: rgba(42,140,114,0.10); color: ${C.success}; }
  .sm-pill-warn { background: rgba(196,122,46,0.10); color: ${C.warn}; }
  .sm-pill-info { background: rgba(111,190,220,0.15); color: ${C.deepTeal}; }

  /* ── Scrollable inner ── */
  .sm-scroll { overflow-y: auto; flex: 1; min-height: 0; }

  /* ── Icon btn ── */
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

  /* ── Fade-up entry ── */
  @keyframes smFadeUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .sm-reveal {
    animation: smFadeUp 0.55s cubic-bezier(0.16,1,0.3,1) both;
  }

  @keyframes smSpin {
    to { transform: rotate(360deg); }
  }
`;

// ─── Colour helpers ───────────────────────────────────────────────────────────
const HEAT_COLORS = {
  high:     "#0F4C5C",
  "med-hi": "#2EC4B6",
  medium:   "#6FBEDC",
  low:      "#B8DDE8",
  none:     "#EEF3F6",
};

function heatVal(v) {
  if (v === null) return "none";
  if (v >= 70) return "high";
  if (v >= 55) return "med-hi";
  if (v >= 40) return "medium";
  return "low";
}

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

// ─── Climate gradient ─────────────────────────────────────────────────────────
function climateColor(v) {
  if (v >= 72) return "#0F4C5C";
  if (v >= 62) return "#2EC4B6";
  if (v >= 52) return "#6FBEDC";
  if (v >= 42) return "#B8DDE8";
  if (v >= 32) return "#E9A848";
  return "#C47A2E";
}

function buildClimate(persons) {
  const hours = ["9 AM","10 AM","11 AM","12 PM","1 PM","2 PM","3 PM","4 PM"];
  if (!persons.length) return { hours, rows: [[],[]] };
  const buckets = hours.map(() => []);
  persons.forEach(p => {
    const s = p.temporal_series || [];
    s.forEach((pt,i) => {
      const b = Math.min(Math.floor(i / Math.max(1, s.length / hours.length)), hours.length - 1);
      buckets[b].push(pt.wellbeing || 50);
    });
  });
  const avgs = buckets.map(b => b.length ? b.reduce((a,v)=>a+v,0)/b.length : 50);
  const row1 = avgs.map((v,i) => ({ color: climateColor(v), label: i===0?Math.round(v)+"":i===4?Math.round(v)+"%":"" }));
  const row2 = avgs.map((v,i) => ({ color: climateColor(Math.max(0, v-6+i*1.1)), label: i===3?Math.round(v)+"%":"" }));
  return { hours, rows:[row1,row2] };
}

function buildHeatGrid(persons) {
  const days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
  const byDay = Object.fromEntries(days.map((_,i)=>[i,[]]));
  persons.forEach(p=>{
    (p.temporal_series||[]).forEach(pt=>{
      if(!pt.date) return;
      const m = pt.date.match(/(\d{4})-(\d{2})-(\d{2})/);
      if(!m) return;
      const d = new Date(`${m[1]}-${m[2]}-${m[3]}`);
      if(!isNaN(d)){
        const wd=(d.getDay()+6)%7;
        byDay[wd].push(pt.wellbeing||50);
      }
    });
  });
  const avgs = days.map((_,i)=>{
    const a=byDay[i];
    return a.length ? a.reduce((s,v)=>s+v,0)/a.length : null;
  });
  const rows = [0,1,2,3].map(r=>avgs.map(avg=>{
    if(avg===null) return "none";
    const shifted = avg+(r-2)*8;
    return heatVal(shifted);
  }));
  return {rows,days};
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function TraitBar({label, value}) {
  const color = barColor(value);
  return (
    <div className="sm-trait-row">
      <div className="sm-trait-header">
        <span className="sm-trait-name">{label}</span>
        <span className="sm-trait-pct" style={{color}}>{value}%</span>
      </div>
      <div className="sm-bar-track">
        <div className="sm-bar-fill" style={{width:`${value}%`, background:color}} />
      </div>
    </div>
  );
}

function KpiCard({label, value, sub, color, delay=0}) {
  return (
    <div className="sm-kpi sm-reveal" style={{animationDelay:`${delay}s`}}>
      <div className="sm-kpi-label">{label}</div>
      <div className="sm-kpi-val" style={{color: color||C.deepTeal}}>{value}</div>
      {sub && <div className="sm-kpi-sub">{sub}</div>}
    </div>
  );
}

function AvatarCircle({name, image, size=30}) {
  if(image) return <img src={`data:image/jpeg;base64,${image}`} alt={name} style={{width:size,height:size,borderRadius:"50%",objectFit:"cover",flexShrink:0}} />;
  const initials = (name||"?").split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase();
  return (
    <div style={{
      width:size, height:size, borderRadius:"50%", flexShrink:0,
      background:`linear-gradient(135deg, ${C.deepTeal}, ${C.aquaTeal})`,
      display:"flex", alignItems:"center", justifyContent:"center",
      fontSize:size>26?11:9, fontWeight:700, color:"#fff", letterSpacing:"0.03em",
    }}>
      {initials}
    </div>
  );
}

function RefreshIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
    </svg>
  );
}

function ChevronUpIcon() {
  return <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="18 15 12 9 6 15"/></svg>;
}

function StarIcon({color=C.aquaTeal}) {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" style={{flexShrink:0}}>
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
    </svg>
  );
}

function WaveIcon() {
  return <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={C.muted} strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>;
}

function UsersIcon() {
  return <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={C.muted} strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>;
}

function TrendBars({bars}) {
  return (
    <div style={{flex:1, display:"flex", height:10, borderRadius:4, overflow:"hidden", gap:2}}>
      {bars.map((b,i)=>(
        <div key={i} style={{width:`${b.pct}%`, background:b.color, borderRadius:3}} />
      ))}
      <div style={{flex:1, background:"#EEF3F6", borderRadius:3}} />
    </div>
  );
}

function buildEngBars(persons) {
  if(!persons.length) return [{pct:60,color:"#EEF3F6"}];
  const t = persons.length;
  const h  = persons.filter(p=>p.average_wellbeing>=70).length/t*100;
  const mh = persons.filter(p=>p.average_wellbeing>=55&&p.average_wellbeing<70).length/t*100;
  const m  = persons.filter(p=>p.average_wellbeing>=40&&p.average_wellbeing<55).length/t*100;
  const l  = persons.filter(p=>p.average_wellbeing<40).length/t*100;
  return [{pct:Math.round(h),color:C.success},{pct:Math.round(mh),color:C.aquaTeal},{pct:Math.round(m),color:C.warn},{pct:Math.round(l),color:C.danger}].filter(b=>b.pct>0);
}

function buildSatBars(persons) {
  if(!persons.length) return [{pct:60,color:"#EEF3F6"}];
  const vals = persons.map(p=>p.avg_traits?.social_confidence||50);
  const t = vals.length;
  const h  = vals.filter(v=>v>=65).length/t*100;
  const mh = vals.filter(v=>v>=50&&v<65).length/t*100;
  const m  = vals.filter(v=>v>=35&&v<50).length/t*100;
  const l  = vals.filter(v=>v<35).length/t*100;
  return [{pct:Math.round(h),color:C.softBlue},{pct:Math.round(mh),color:C.aquaTeal},{pct:Math.round(m),color:C.warn},{pct:Math.round(l),color:C.danger}].filter(b=>b.pct>0);
}

function buildPeerBars(persons, intervention) {
  if(!persons.length) return [{pct:60,color:"#EEF3F6"}];
  const good = Math.max(0,persons.length-intervention)/persons.length*100;
  const warn = Math.min(intervention,persons.length)/persons.length*100;
  return [{pct:Math.round(good*0.4),color:C.softBlue},{pct:Math.round(good*0.5),color:C.aquaTeal},{pct:Math.round(warn),color:C.warn}].filter(b=>b.pct>0);
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function PrincipalDashboard() {
  const { user } = useSession();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeNav, setActiveNav] = useState("Dashboard");
  const [activeTab, setActiveTab] = useState("Overview");
  const [selectedSchool, setSelectedSchool] = useState(null);
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    fetchReport();
  }, []);

  async function fetchReport() {
    setLoading(true);
    setError(null);
    try {
      const data = await authFetch("/analysis/report");
      if (data.success && data.report) {
        setReport(data.report);
        const schools = data.report.overall_stats?.schools || [];
        if (schools.length) setSelectedSchool(schools[0]);
      } else {
        setError("No report available. Run analysis first.");
      }
    } catch (e) {
      setError("Cannot connect to backend. Make sure the Flask server is running.");
    }
    setLoading(false);
  }

  // ── Derived data ────────────────────────────────────────────────────────────
  const persons = report ? Object.values(report.person_profiles) : [];
  const stats = report?.overall_stats || {};
  const schools = stats.schools || [];
  const atRisk = persons.filter(p=>p.average_wellbeing<50);

  const schoolPersons = selectedSchool
    ? persons.filter(p=>p.school===selectedSchool)
    : persons;

  const avgWb = schoolPersons.length
    ? Math.round(schoolPersons.reduce((a,p)=>a+p.average_wellbeing,0)/schoolPersons.length) : 0;

  const avgEng = schoolPersons.length
    ? Math.round(schoolPersons.reduce((a,p)=>a+p.average_engagement,0)/schoolPersons.length) : 0;

  const improving = persons.filter(p=>{
    const tr = p.wellbeing_trend||[];
    return tr.length>=2 && tr[tr.length-1]>tr[0];
  });
  const engImprove = persons.length ? Math.round(improving.length/persons.length*100) : 0;

  const peerIssues = persons.filter(p=>{
    const t = p.avg_traits||{};
    return (t.social_engagement||50)<45||(t.social_confidence||50)<45;
  }).length;

  const pinnedIds = report?.pinned_profiles||[];
  const pinned = pinnedIds.map(id=>report?.person_profiles[id]).filter(Boolean);
  const topStudents = [
    ...pinned,
    ...persons.filter(p=>!pinned.find(pp=>pp.person_id===p.person_id))
      .sort((a,b)=>b.total_detections-a.total_detections),
  ].slice(0,6);

  const {rows:heatRows, days:heatDays} = buildHeatGrid(schoolPersons);
  const {hours:climHours, rows:climRows} = buildClimate(persons);
  const schoolAtRisk = selectedSchool ? atRisk.filter(p=>p.school===selectedSchool) : atRisk;

  // ── Loading ─────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="sm-dash" style={{alignItems:"center",justifyContent:"center",gap:14}}>
        <style>{GLOBAL_CSS}</style>
        <div style={{
          width:32, height:32, border:"2.5px solid #EEF3F6",
          borderTopColor:C.aquaTeal, borderRadius:"50%",
          animation:"smSpin 0.7s linear infinite",
        }} />
        <span style={{fontSize:13,color:C.muted}}>Loading report…</span>
      </div>
    );
  }

  // ── Error ───────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="sm-dash" style={{alignItems:"center",justifyContent:"center",gap:12,padding:40}}>
        <style>{GLOBAL_CSS}</style>
        <div style={{fontSize:36}}>⚠️</div>
        <div style={{fontFamily:"'Poppins',sans-serif",fontSize:16,fontWeight:700,color:C.deepTeal}}>Connection Error</div>
        <div style={{fontSize:13,color:C.muted,textAlign:"center",maxWidth:400}}>{error}</div>
        <button
          onClick={fetchReport}
          style={{
            marginTop:8,padding:"9px 22px",
            background:`linear-gradient(135deg, ${C.deepTeal}, ${C.aquaTeal})`,
            color:"#fff",border:"none",borderRadius:10,
            fontSize:14,fontWeight:600,cursor:"pointer",
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="sm-dash">
      <style>{GLOBAL_CSS}</style>

      {/* ── NAVBAR ─────────────────────────────────────────────────────────── */}
      <nav className="sm-nav">
        {/* Logo */}
        <img src={icon} alt="Sentio Mind" style={{ width: 210, height: 70 }} />
        <div style={{ flex: 1 }} />
        {/* Nav links */}
        {["Dashboard","Reports","Alerts","Settings"].map(t=>(
          <button
            key={t}
            className={`sm-nav-link${activeNav===t?" active":""}`}
            onClick={()=>setActiveNav(t)}
            style={{position:"relative"}}
          >
            {t==="Alerts" && atRisk.length>0 && (
              <span style={{
                background:C.danger, color:"#fff", borderRadius:999,
                fontSize:9, fontWeight:700, padding:"1px 5px", marginRight:4,
              }}>{atRisk.length}</span>
            )}
            {t}
          </button>
        ))}

        <div style={{flex:1}} />

        {/* Live pill */}
        <div className="sm-pill sm-pill-live">
          <span style={{width:7,height:7,borderRadius:"50%",background:C.success,flexShrink:0}} />
          {persons.length} tracked
        </div>

        {/* School selector */}
        {schools.length>1 && (
          <select className="sm-select" value={selectedSchool||""} onChange={e=>setSelectedSchool(e.target.value)}>
            {schools.map(s=><option key={s} value={s}>{s}</option>)}
          </select>
        )}

        {/* Refresh */}
        <button className="sm-icon-btn" onClick={fetchReport} title="Refresh">
          <RefreshIcon />
        </button>

        {/* User + Logout */}
        <span style={{fontSize:13,fontWeight:500,color:C.charcoal}}>{user?.email || "Principal"}</span>
        <LogoutButton />
      </nav>

      {/* ── BODY ───────────────────────────────────────────────────────────── */}
      <div className="sm-body">

        {/* Page header */}
        <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:14,flexShrink:0}}>
          <div>
            <h1 style={{fontFamily:"'Poppins',sans-serif",fontSize:20,fontWeight:800,color:C.deepTeal,letterSpacing:"-0.03em",lineHeight:1}}>
              Principal Dashboard
            </h1>
            <p style={{fontSize:11,color:C.muted,marginTop:3}}>{stats.date_range?.join(" — ")} · {stats.total_dates_analyzed} days analysed</p>
          </div>
          <div className="sm-pill sm-pill-info" style={{fontSize:11}}>
            {selectedSchool || "All Schools"}
          </div>
        </div>

        {/* KPI row */}
        <div style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:10,marginBottom:14,flexShrink:0}}>
          <KpiCard label="Total Students" value={stats.total_unique_persons||0} sub={`${stats.total_schools||0} school(s)`} delay={0} />
          <KpiCard label="Avg Wellbeing" value={`${avgWb}%`} sub={wbLabel(avgWb)} color={wbColor(avgWb)} delay={0.05} />
          <KpiCard label="Avg Engagement" value={`${avgEng}%`} sub="Across cohort" color={C.deepTeal} delay={0.1} />
          <KpiCard label="Days Analysed" value={stats.total_dates_analyzed||0} sub={stats.date_range?.join(" → ")} delay={0.15} />
          <KpiCard label="Needs Monitoring" value={atRisk.length} sub="Wellbeing below 50%" color={atRisk.length>0?C.danger:C.success} delay={0.2} />
        </div>

        {/* Main grid */}
        <div style={{display:"grid",gridTemplateColumns:"360px 1fr",gap:12,flex:1,overflow:"hidden",minHeight:0}}>

          {/* ── LEFT COLUMN ─────────────────────────────────────────────── */}
          <div style={{display:"flex",flexDirection:"column",gap:10,overflow:"hidden",minHeight:0}}>

            {/* Students panel */}
            <div className="sm-card sm-reveal" style={{animationDelay:"0.1s"}}>
              <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:10}}>
                <div style={{display:"flex",alignItems:"center",gap:6}}>
                  <UsersIcon />
                  <span className="sm-card-title" style={{margin:0}}>Students Tracked</span>
                </div>
                <span style={{fontSize:11,color:C.muted}}>{schoolPersons.length} in cohort</span>
              </div>

              {topStudents.length===0 && (
                <div style={{fontSize:12,color:C.muted,padding:"10px 0"}}>No data yet — run analysis first.</div>
              )}

              {topStudents.map((p,i)=>{
                const isPinned = pinnedIds.includes(p.person_id);
                const color = wbColor(p.average_wellbeing);
                return (
                  <div key={p.person_id} className="sm-person-row" style={{animationDelay:`${0.15+i*0.04}s`}}>
                    <AvatarCircle name={p.name} image={p.profile_image} />
                    <span style={{fontSize:12,fontWeight:500,flex:1,color:C.charcoal}}>{p.name}</span>
                    {isPinned && (
                      <span style={{fontSize:9,color:C.deepTeal,background:"rgba(15,76,92,0.08)",borderRadius:4,padding:"2px 5px",fontWeight:700,letterSpacing:"0.06em"}}>PINNED</span>
                    )}
                    <div style={{display:"flex",flexDirection:"column",alignItems:"flex-end",gap:2}}>
                      <span style={{fontSize:12,fontWeight:800,color}}>{p.average_wellbeing}%</span>
                      <div style={{width:40,height:3,background:"#EEF3F6",borderRadius:2,overflow:"hidden"}}>
                        <div style={{width:`${p.average_wellbeing}%`,height:"100%",background:color,borderRadius:2}} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Heat grid */}
            <div className="sm-card sm-reveal" style={{flex:1,overflow:"hidden",display:"flex",flexDirection:"column",animationDelay:"0.18s"}}>
              <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:10}}>
                <div style={{display:"flex",alignItems:"center",gap:6}}>
                  <WaveIcon />
                  <span className="sm-card-title" style={{margin:0}}>Weekly Behaviour Heat</span>
                </div>
                <span style={{fontSize:10,color:C.muted}}>{selectedSchool||"All"}</span>
              </div>

              <div style={{display:"flex",justifyContent:"space-between",fontSize:10,color:C.muted,marginBottom:5}}>
                <span>Intensity</span><span>Incidents</span>
              </div>

              <div style={{display:"flex",flexDirection:"column",gap:4,flex:1}}>
                {[3,2,1,0].map(ri=>(
                  <div key={ri} style={{display:"flex",alignItems:"center",gap:3}}>
                    <span style={{fontSize:9,color:C.muted,width:10,textAlign:"right",marginRight:3}}>{ri+1}</span>
                    {heatDays.map((_,ci)=>(
                      <div
                        key={ci}
                        className="sm-heat-cell"
                        style={{background:HEAT_COLORS[(heatRows[ri]||[])[ci]||"none"]}}
                        title={`${heatDays[ci]}: ${(heatRows[ri]||[])[ci]||"no data"}`}
                      />
                    ))}
                  </div>
                ))}
                <div style={{display:"flex",gap:3,paddingLeft:16,marginTop:2}}>
                  {heatDays.map(d=>(
                    <span key={d} style={{fontSize:9,color:C.muted,flex:1,textAlign:"center"}}>{d}</span>
                  ))}
                </div>
              </div>

              {/* Legend */}
              <div style={{display:"flex",gap:10,marginTop:8,flexWrap:"wrap"}}>
                {[
                  {color:HEAT_COLORS.high,label:"High"},
                  {color:HEAT_COLORS["med-hi"],label:"Med-High"},
                  {color:HEAT_COLORS.medium,label:"Medium"},
                  {color:HEAT_COLORS.low,label:"Low"},
                  {color:HEAT_COLORS.none,label:"No Data"},
                ].map(({color,label})=>(
                  <div key={label} style={{display:"flex",alignItems:"center",gap:4}}>
                    <div style={{width:9,height:9,borderRadius:2,background:color,border:`1px solid ${C.border}`}} />
                    <span style={{fontSize:9,color:C.muted}}>{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ── RIGHT COLUMN ────────────────────────────────────────────── */}
          <div style={{display:"flex",flexDirection:"column",gap:10,overflow:"hidden",minHeight:0}}>

            {/* Emotional climate map */}
            <div className="sm-card sm-reveal" style={{padding:"16px 18px 12px",animationDelay:"0.22s"}}>
              <h2 style={{fontFamily:"'Poppins',sans-serif",fontSize:14,fontWeight:700,color:C.deepTeal,margin:"0 0 12px",letterSpacing:"-0.01em"}}>
                School-Wide Emotional Climate
                <span style={{fontSize:11,color:C.muted,fontWeight:400,marginLeft:8}}>
                  {persons.length} students · {stats.total_dates_analyzed||0} days
                </span>
              </h2>

              {persons.length===0 ? (
                <div style={{height:72,display:"flex",alignItems:"center",justifyContent:"center",background:"#F7F9FB",borderRadius:10,color:C.muted,fontSize:12}}>
                  No data — run analysis first
                </div>
              ) : (
                <>
                  <div style={{borderRadius:10,overflow:"hidden",marginBottom:6}}>
                    {climRows.map((row,ri)=>(
                      <div key={ri}>
                        {ri>0 && <div style={{height:2,background:C.offWhite}} />}
                        <div style={{display:"flex",height:60}}>
                          {row.map((cell,ci)=>(
                            <div
                              key={ci}
                              className="sm-climate-cell"
                              style={{background:cell.color}}
                              onMouseEnter={()=>setTooltip(`${ri}-${ci}`)}
                              onMouseLeave={()=>setTooltip(null)}
                            >
                              {cell.label||""}
                              {tooltip===`${ri}-${ci}` && (
                                <div style={{
                                  position:"absolute",
                                  [ri===0?"top":"bottom"]:"110%",
                                  left:"50%", transform:"translateX(-50%)",
                                  background:"#fff",
                                  border:`1px solid ${C.border}`,
                                  borderRadius:8,
                                  padding:"4px 10px",
                                  fontSize:11, color:C.charcoal,
                                  boxShadow:"0 2px 12px rgba(15,76,92,0.10)",
                                  zIndex:20, whiteSpace:"nowrap",
                                  pointerEvents:"none",
                                }}>
                                  {climHours[ci]}: {cell.label||"—"}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div style={{display:"flex",justifyContent:"space-between",fontSize:10,color:C.muted}}>
                    {climHours.map(h=><span key={h}>{h}</span>)}
                  </div>
                </>
              )}
            </div>

            {/* Semester trend */}
            <div className="sm-card sm-reveal" style={{flex:1,padding:"16px 18px",display:"flex",flexDirection:"column",overflow:"hidden",animationDelay:"0.26s"}}>
              <h2 style={{fontFamily:"'Poppins',sans-serif",fontSize:14,fontWeight:700,color:C.deepTeal,margin:"0 0 10px",letterSpacing:"-0.01em"}}>
                Semester Trend
              </h2>

              {/* Tabs */}
              <div style={{display:"flex",gap:18,borderBottom:`1px solid ${C.border}`,marginBottom:14}}>
                {["Overview","Engagement","Wellbeing"].map(tab=>(
                  <button
                    key={tab}
                    className={`sm-tab${activeTab===tab?" active":""}`}
                    onClick={()=>setActiveTab(tab)}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {/* Positive dev header */}
              <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:14}}>
                <h3 style={{margin:0,fontSize:14,fontWeight:700,color:C.charcoal}}>Positive Development</h3>
                {engImprove>0 && (
                  <span className="sm-pill sm-pill-warn">
                    {improving.length}P · {engImprove}%
                  </span>
                )}
                <span style={{border:`1px solid ${C.border}`,borderRadius:100,fontSize:11,padding:"3px 12px",color:C.muted}}>
                  {stats.total_dates_analyzed||0} days
                </span>
              </div>

              {/* Trend rows */}
              <div className="sm-trend-row">
                <StarIcon color={C.success} />
                <span style={{fontSize:12,color:C.charcoal,minWidth:190}}>Engagement Improvement</span>
                <span style={{fontSize:12,fontWeight:800,color:C.success,minWidth:36}}>{engImprove}%</span>
                <TrendBars bars={buildEngBars(persons)} />
              </div>

              <div className="sm-trend-row">
                <StarIcon color={C.warn} />
                <span style={{fontSize:12,color:C.charcoal,minWidth:190}}>Satisfaction Concerns</span>
                <span style={{fontSize:12,fontWeight:800,color:C.charcoal,minWidth:36}}>{atRisk.length}</span>
                <TrendBars bars={buildSatBars(persons)} />
              </div>

              <div className="sm-trend-row">
                <StarIcon color={C.warn} />
                <span style={{fontSize:12,color:C.charcoal,minWidth:190}}>Peer Relationships — Intervention</span>
                <span style={{minWidth:36}} />
                <TrendBars bars={buildPeerBars(persons, peerIssues)} />
              </div>

              {/* At-risk section */}
              {schoolAtRisk.length>0 && (
                <div className="sm-risk-panel">
                  <div className="sm-risk-label">Needs Monitoring ({schoolAtRisk.length})</div>
                  <div style={{display:"flex",flexDirection:"column",gap:7,maxHeight:110,overflowY:"auto"}}>
                    {schoolAtRisk.slice(0,4).map(p=>{
                      const lowest = p.avg_traits
                        ? Object.entries(p.avg_traits).sort((a,b)=>a[1]-b[1])[0]
                        : null;
                      return (
                        <div key={p.person_id} style={{display:"flex",alignItems:"center",gap:8}}>
                          <AvatarCircle name={p.name} image={p.profile_image} size={28} />
                          <div style={{flex:1,minWidth:0}}>
                            <div style={{fontSize:12,fontWeight:600,color:C.charcoal}}>{p.name}</div>
                            {lowest && (
                              <div style={{fontSize:10,color:C.muted}}>
                                Lowest: {lowest[0].replace(/_/g," ")} ({lowest[1]}%)
                              </div>
                            )}
                          </div>
                          <span style={{fontSize:13,fontWeight:800,color:C.danger}}>{p.average_wellbeing}%</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Trait breakdown for first at-risk student */}
              {schoolAtRisk.length>0 && (
                <div style={{marginTop:12,flex:1,overflow:"hidden"}}>
                  <div style={{fontSize:11,fontWeight:600,color:C.muted,letterSpacing:"0.08em",textTransform:"uppercase",marginBottom:8}}>
                    Top concern — {schoolAtRisk[0].name}
                  </div>
                  <div className="sm-scroll">
                    {Object.entries(schoolAtRisk[0].avg_traits||{}).slice(0,6).map(([k,v])=>(
                      <TraitBar key={k} label={k.replace(/_/g," ")} value={v} />
                    ))}
                  </div>
                </div>
              )}

              {/* Stress footer */}
              <div style={{
                borderTop:`1px solid #EEF3F6`,
                paddingTop:10,
                marginTop:"auto",
                display:"flex",
                alignItems:"center",
                justifyContent:"space-between",
                flexShrink:0,
              }}>
                <span style={{fontSize:12,color:C.charcoal}}>Stress Level — Positive Disengagements</span>
                <span style={{fontSize:11,color:C.muted}}>
                  {persons.filter(p=>{
                    const last = p.temporal_series?.at(-1);
                    return last?.traits?.stress_resilience<40;
                  }).length} high-stress detected
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}