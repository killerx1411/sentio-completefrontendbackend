"""Operator dashboard template for the CV system (served at ``GET /``).

Static HTML/JS only — extracted verbatim from the previous ``test_db.py`` so
the dashboard renders exactly as before.
"""

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sentio Mind — Behavioral Intelligence</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root {
  --bg:#f5f5f0;--surface:#fff;--surface2:#f0eeea;--border:#e2e0db;--border2:#d4d2cc;
  --text-primary:#1a1917;--text-secondary:#5c5b57;--text-muted:#9b9994;
  --accent:#2563eb;--accent-light:#eff6ff;--accent-mid:#bfdbfe;
  --green:#059669;--green-light:#ecfdf5;--amber:#d97706;--amber-light:#fffbeb;
  --red:#dc2626;--red-light:#fef2f2;--pin:#7c3aed;--pin-light:#f5f3ff;
  --shadow-sm:0 1px 3px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);
  --shadow-md:0 4px 16px rgba(0,0,0,.08),0 2px 6px rgba(0,0,0,.04);
  --shadow-lg:0 12px 40px rgba(0,0,0,.10),0 4px 12px rgba(0,0,0,.05);
  --radius:12px;--radius-sm:8px;--radius-lg:20px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:'DM Sans',system-ui,sans-serif;background:var(--bg);color:var(--text-primary);line-height:1.6;-webkit-font-smoothing:antialiased}
.hero{background:rgba(255,255,255,.92);border-bottom:1px solid var(--border);padding:0 48px;position:sticky;top:0;z-index:100;backdrop-filter:blur(12px)}
.hero-inner{max-width:1400px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:68px}
.logo-wrap{display:flex;align-items:center;gap:12px}
.brain-svg{width:36px;height:36px;flex-shrink:0}
.logo-name{font-family:'Syne',sans-serif;font-weight:800;font-size:1.25rem;letter-spacing:-.02em}
.logo-sub{font-size:.7rem;color:var(--text-muted);font-weight:400;letter-spacing:.08em;text-transform:uppercase;margin-top:-2px}
.nav-links{display:flex;align-items:center;gap:2px}
.nav-link{padding:8px 16px;border-radius:var(--radius-sm);font-size:.875rem;font-weight:500;color:var(--text-secondary);cursor:pointer;transition:all .2s;border:none;background:transparent}
.nav-link:hover{background:var(--surface2);color:var(--text-primary)}
.nav-link.active{background:var(--accent-light);color:var(--accent);font-weight:600}
.nav-badge{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;background:var(--green-light);color:var(--green);border-radius:20px;font-size:.75rem;font-weight:600}
.dot-live{width:7px;height:7px;background:var(--green);border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.page-section{display:none}.page-section.active{display:block}

/* LANDING */
.landing-hero{background:var(--surface);padding:96px 48px 80px;border-bottom:1px solid var(--border);text-align:center}
.landing-hero-inner{max-width:780px;margin:0 auto}
.hero-eyebrow{display:inline-flex;align-items:center;gap:8px;padding:6px 14px;background:var(--accent-light);border:1px solid var(--accent-mid);border-radius:20px;font-size:.75rem;font-weight:600;color:var(--accent);letter-spacing:.04em;text-transform:uppercase;margin-bottom:32px}
.landing-hero h1{font-family:'Syne',sans-serif;font-size:clamp(2.5rem,5vw,4rem);font-weight:800;letter-spacing:-.03em;line-height:1.1;margin-bottom:24px}
.landing-hero h1 em{font-style:normal;color:var(--accent)}
.landing-hero p{font-size:1.125rem;color:var(--text-secondary);font-weight:300;max-width:560px;margin:0 auto 48px;line-height:1.7}
.hero-cta{display:flex;gap:12px;justify-content:center;align-items:center;flex-wrap:wrap}
.schools-section{padding:56px 48px;background:var(--bg)}
.schools-inner{max-width:1400px;margin:0 auto}
.schools-label{font-size:.75rem;font-weight:600;color:var(--text-muted);letter-spacing:.1em;text-transform:uppercase;text-align:center;margin-bottom:32px}
.schools-grid{display:flex;flex-wrap:wrap;gap:12px;justify-content:center}
.school-chip{padding:10px 20px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);font-size:.875rem;font-weight:500;color:var(--text-secondary);transition:all .2s;cursor:default}
.school-chip:hover{border-color:var(--accent-mid);color:var(--accent)}
.features-section{padding:80px 48px;background:var(--surface);border-top:1px solid var(--border);border-bottom:1px solid var(--border)}
.features-inner{max-width:1400px;margin:0 auto}
.section-header{text-align:center;margin-bottom:56px}
.section-tag{display:inline-block;padding:4px 12px;background:var(--surface2);border-radius:4px;font-size:.7rem;font-weight:700;color:var(--text-muted);letter-spacing:.1em;text-transform:uppercase;margin-bottom:16px}
.section-header h2{font-family:'Syne',sans-serif;font-size:2.25rem;font-weight:800;letter-spacing:-.025em;line-height:1.2}
.features-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}
.feature-card{padding:32px;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-lg);transition:all .3s}
.feature-card:hover{box-shadow:var(--shadow-md);border-color:var(--border2);transform:translateY(-2px)}
.feature-icon{width:48px;height:48px;background:var(--accent-light);border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;margin-bottom:20px}
.feature-card h3{font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;margin-bottom:10px}
.feature-card p{font-size:.875rem;color:var(--text-secondary);line-height:1.7}

/* DASHBOARD */
.dashboard-wrap{max-width:1400px;margin:0 auto;padding:40px 48px}
.dash-topbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:32px}
.dash-title{font-family:'Syne',sans-serif;font-size:1.625rem;font-weight:800;letter-spacing:-.025em}
.dash-sub{font-size:.875rem;color:var(--text-muted);margin-top:2px}
.btn{display:inline-flex;align-items:center;gap:8px;padding:10px 20px;border-radius:var(--radius-sm);font-size:.875rem;font-weight:600;cursor:pointer;transition:all .2s;border:none;font-family:inherit;white-space:nowrap}
.btn-primary{background:var(--accent);color:#fff}.btn-primary:hover{background:#1d4ed8;box-shadow:0 4px 12px rgba(37,99,235,.3);transform:translateY(-1px)}.btn-primary:disabled{opacity:.55;cursor:not-allowed;transform:none}
.btn-ghost{background:var(--surface);border:1px solid var(--border);color:var(--text-secondary)}.btn-ghost:hover{border-color:var(--border2);color:var(--text-primary)}
.btn-pin{background:var(--pin-light);border:1px solid #ddd6fe;color:var(--pin)}.btn-pin:hover{background:#ede9fe;border-color:#c4b5fd}
.btn-lg{padding:14px 28px;font-size:.9375rem;border-radius:var(--radius)}
.btn-sm{padding:7px 14px;font-size:.8125rem}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-bottom:32px}
.kpi-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:24px;transition:all .2s}.kpi-card:hover{box-shadow:var(--shadow-md)}
.kpi-label{font-size:.75rem;font-weight:600;color:var(--text-muted);letter-spacing:.06em;text-transform:uppercase;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.kpi-num{font-family:'Syne',sans-serif;font-size:2.25rem;font-weight:800;letter-spacing:-.03em;line-height:1}
.kpi-unit{font-size:1rem;color:var(--text-muted);font-weight:400;margin-left:3px}
.kpi-meta{font-size:.8rem;color:var(--text-muted);margin-top:8px}
.kpi-good{color:var(--green)!important}.kpi-warn{color:var(--amber)!important}.kpi-bad{color:var(--red)!important}
.content-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);margin-bottom:24px;overflow:hidden}
.content-card-header{padding:24px 28px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}
.content-card-title{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;display:flex;align-items:center;gap:10px}
.content-card-body{padding:28px}

/* PINNED SECTION */
.pinned-banner{background:linear-gradient(135deg,#f5f3ff,#ede9fe);border:1px solid #c4b5fd;border-radius:var(--radius-lg);padding:20px 24px;margin-bottom:24px}
.pinned-banner-title{font-family:'Syne',sans-serif;font-size:.95rem;font-weight:800;color:var(--pin);display:flex;align-items:center;gap:8px;margin-bottom:14px}
.pinned-grid{display:flex;gap:12px;flex-wrap:wrap}
.pinned-chip{display:flex;align-items:center;gap:10px;padding:10px 14px;background:white;border:1px solid #c4b5fd;border-radius:10px;cursor:pointer;transition:all .2s}
.pinned-chip:hover{box-shadow:var(--shadow-sm);transform:translateY(-1px)}
.pinned-chip img{width:36px;height:36px;border-radius:6px;object-fit:cover;border:1px solid #c4b5fd}
.pinned-chip-name{font-weight:600;font-size:.8rem;color:var(--text-primary)}
.pinned-chip-wb{font-family:'Syne',sans-serif;font-size:.9rem;font-weight:800}
.unpin-btn{font-size:.65rem;color:#a78bfa;cursor:pointer;margin-left:4px}
.unpin-btn:hover{color:var(--pin)}

/* PERSON CARDS */
.person-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:20px}
.person-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);transition:all .25s;overflow:hidden}
.person-card:hover{box-shadow:var(--shadow-md);border-color:var(--border2)}
.person-card.flagged{border-color:#fca5a5;background:var(--red-light)}
.person-card.warn{border-color:#fcd34d;background:var(--amber-light)}
.person-card.pinned-card{border-color:#c4b5fd;box-shadow:0 0 0 2px #ede9fe}
.person-name{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;cursor:pointer;transition:color .2s}
.person-name:hover{color:var(--accent)}
.well-track{width:100%;height:6px;background:var(--surface2);border-radius:3px;margin:10px 0;overflow:hidden}
.well-fill{height:100%;border-radius:3px;transition:width .6s ease}
.well-high{background:linear-gradient(90deg,#10b981,#059669)}
.well-mid{background:linear-gradient(90deg,#f59e0b,#d97706)}
.well-low{background:linear-gradient(90deg,#ef4444,#dc2626)}
.tag{padding:3px 8px;border-radius:4px;font-size:.7rem;font-weight:600;letter-spacing:.03em;text-transform:uppercase}
.tag-blue{background:var(--accent-light);color:var(--accent)}
.tag-green{background:var(--green-light);color:var(--green)}
.tag-amber{background:var(--amber-light);color:var(--amber)}
.tag-red{background:var(--red-light);color:var(--red)}
.tag-pin{background:var(--pin-light);color:var(--pin)}

/* GAZE VISUALISER */
.gaze-eye-box{display:inline-flex;align-items:center;justify-content:center;width:48px;height:32px;background:#f8faff;border:1.5px solid var(--border);border-radius:20px;position:relative;overflow:hidden}
.gaze-iris{width:12px;height:12px;background:var(--accent);border-radius:50%;position:absolute;transition:all .3s;box-shadow:0 0 0 2px rgba(37,99,235,.2)}
.gaze-label-row{display:flex;align-items:center;gap:8px;margin-top:6px}
.gaze-dir-badge{padding:2px 8px;border-radius:4px;font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.gaze-forward{background:#dcfce7;color:#15803d}
.gaze-left,.gaze-right{background:#fef9c3;color:#a16207}
.gaze-up,.gaze-down{background:#e0e7ff;color:#4338ca}
.gaze-camera{background:var(--green-light);color:var(--green)}
.gaze-distracted{background:var(--red-light);color:var(--red)}

/* MISC */
.date-strip{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:28px}
.date-pill{padding:8px 16px;background:var(--surface);border:1px solid var(--border);border-radius:8px;font-size:.8125rem;font-weight:600;cursor:pointer;transition:all .2s;color:var(--text-secondary)}
.date-pill:hover{border-color:var(--accent-mid);color:var(--accent)}
.date-pill.active{background:var(--accent-light);border-color:var(--accent-mid);color:var(--accent)}
.timeline-stream{display:flex;flex-direction:column;gap:16px}
.tl-item{display:flex;gap:20px;align-items:flex-start}
.tl-dot{width:10px;height:10px;border-radius:50%;background:var(--accent);border:2px solid var(--accent-mid);flex-shrink:0}
.tl-line{width:2px;background:var(--border);flex:1;margin-top:4px;min-height:32px}
.tl-body{flex:1;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);padding:16px 20px;margin-bottom:4px}
.tl-date{font-size:.75rem;font-weight:700;color:var(--accent);letter-spacing:.04em;text-transform:uppercase;margin-bottom:6px}
.tl-person{font-size:.9375rem;font-weight:600;margin-bottom:4px}
.tl-meta{font-size:.8125rem;color:var(--text-secondary)}
.empty-state{text-align:center;padding:80px 24px;color:var(--text-muted)}
.empty-icon{font-size:3rem;margin-bottom:16px;opacity:.35}
.empty-title{font-size:1.125rem;font-weight:600;color:var(--text-secondary);margin-bottom:8px}
.empty-sub{font-size:.875rem}
.loading-overlay{display:none;position:fixed;inset:0;background:rgba(245,245,240,.88);backdrop-filter:blur(8px);z-index:999;align-items:center;justify-content:center;flex-direction:column;gap:20px}
.loading-overlay.active{display:flex}
.spinner{width:48px;height:48px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-title{font-family:'Syne',sans-serif;font-size:1.25rem;font-weight:700}
.loading-sub{font-size:.875rem;color:var(--text-secondary)}
.settings-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.settings-row{padding:20px 24px;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-sm);display:flex;justify-content:space-between;align-items:center}
.settings-key{font-size:.875rem;font-weight:600;color:var(--text-secondary)}
.settings-val{font-size:.875rem;color:var(--text-primary);font-weight:700;font-family:monospace;background:var(--surface);padding:4px 10px;border-radius:4px;border:1px solid var(--border)}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(26,25,23,.5);z-index:200;align-items:center;justify-content:center}
.modal-overlay.active{display:flex}
.modal{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:32px;width:480px;max-width:90vw;box-shadow:var(--shadow-lg)}
.modal h3{font-family:'Syne',sans-serif;font-size:1.25rem;font-weight:800;margin-bottom:8px}
.modal p{font-size:.875rem;color:var(--text-secondary);margin-bottom:20px}
.modal-input{width:100%;padding:12px 16px;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-sm);font-size:.9375rem;font-family:inherit;margin-bottom:20px;outline:none;transition:border-color .2s}
.modal-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(37,99,235,.1)}
.modal-actions{display:flex;gap:10px;justify-content:flex-end}
.metric-item{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--surface2);font-size:.8125rem}
.metric-item:last-child{border-bottom:none}
.metric-k{color:var(--text-muted);font-weight:500}
.metric-v{color:var(--text-primary);font-weight:700}
@media(max-width:900px){.hero,.dashboard-wrap,.landing-hero,.schools-section,.features-section{padding-left:20px;padding-right:20px}.contacts-grid,.settings-grid{grid-template-columns:1fr}}
</style>
</head>
<body>

<nav class="hero">
  <div class="hero-inner">
    <div class="logo-wrap">
      <svg class="brain-svg" viewBox="0 0 64 64" fill="none">
        <rect width="64" height="64" rx="14" fill="#eff6ff"/>
        <path d="M22 28c0-5.523 4.477-10 10-10s10 4.477 10 10c0 1.5-.33 2.92-.918 4.194C43.012 33.36 44 35.07 44 37c0 3.314-2.686 6-6 6a5.98 5.98 0 01-3-.798A5.98 5.98 0 0132 43a5.98 5.98 0 01-3 .798A6 6 0 0120 37c0-1.93.988-3.64 2.918-4.806A9.96 9.96 0 0122 28z" fill="#dbeafe" stroke="#2563eb" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M32 18v25M22 28c3 0 5 2 5 5s-2 4-5 4M42 28c-3 0-5 2-5 5s2 4 5 4" stroke="#2563eb" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="32" cy="28" r="3" fill="#2563eb"/>
      </svg>
      <div><div class="logo-name">Sentio Mind</div><div class="logo-sub">Behavioral Intelligence</div></div>
    </div>
    <div class="nav-links">
      <button class="nav-link active" onclick="goTo('home',this)">Home</button>
      <button class="nav-link" onclick="goTo('dashboard',this)">Dashboard</button>
      <button class="nav-link" onclick="goTo('profiles',this)">Profiles</button>
      <button class="nav-link" onclick="goTo('temporal',this)">Temporal</button>
      <button class="nav-link" onclick="goTo('daily',this)">Daily</button>
      <button class="nav-link" onclick="goTo('timeline',this)">Timeline</button>
      <button class="nav-link" onclick="goTo('settings',this)">Settings</button>
    </div>
    <div class="nav-badge"><div class="dot-live"></div>System Active</div>
  </div>
</nav>

<!-- HOME -->
<div id="page-home" class="page-section active">
  <section class="landing-hero">
    <div class="landing-hero-inner">
      <div class="hero-eyebrow">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M7 4v3l2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        AI-Powered CCTV Analytics
      </div>
      <h1>Understand <em>behavior.</em><br>Unlock wellbeing.</h1>
      <p>Sentio Mind uses state-of-the-art computer vision — MTCNN + face_recognition + MediaPipe — to analyze CCTV footage at multiple scales, detect every individual even in low-resolution footage, and track gaze, posture, and wellbeing across days.</p>
      <div class="hero-cta">
        <button class="btn btn-primary btn-lg" onclick="goToAndAnalyze()">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5,3 19,12 5,21"/></svg>
          Start Analysis
        </button>
        <button class="btn btn-ghost btn-lg" onclick="goTo('dashboard',document.querySelectorAll('.nav-link')[1])">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          Open Dashboard
        </button>
      </div>
    </div>
  </section>
  <section class="schools-section"><div class="schools-inner">
    <div class="schools-label">Trusted by institutions across the country</div>
    <div class="schools-grid">
      <div class="school-chip">Delhi Public School</div><div class="school-chip">Ryan International</div>
      <div class="school-chip">Kendriya Vidyalaya</div><div class="school-chip">Podar International</div>
      <div class="school-chip">The Heritage School</div><div class="school-chip">Amity School Network</div>
      <div class="school-chip">Greenwood High</div><div class="school-chip">National Public School</div>
    </div>
  </div></section>
  <section class="features-section"><div class="features-inner">
    <div class="section-header"><div class="section-tag">Capabilities</div><h2>Everything you need,<br>built in one platform</h2></div>
    <div class="features-grid">
      <div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg></div><h3>MTCNN + Multi-Scale Detection</h3><p>MTCNN, face_recognition (HOG+CNN), MediaPipe, and Haar cascade run in ensemble on both original and 2× upscaled frames — maximising detection on low-pixel CCTV footage.</p></div>
      <div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg></div><h3>Gaze & Attention Analysis</h3><p>MediaPipe Face Mesh iris landmarks detect gaze direction (forward/left/right/up/down), head pose (yaw/pitch), eye contact, and compute a 0–100 attention score per person.</p></div>
      <div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg></div><h3>10-Trait Wellbeing Profile</h3><p>Emotion, posture, gaze, and texture combine into 10 behavioural traits — positivity, resilience, energy, posture, focus/alertness, vitality and more — with a weighted overall score.</p></div>
      <div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg></div><h3>Pin Profiles to Dashboard</h3><p>Pin any individual's profile card directly to the dashboard for at-a-glance monitoring. Pinned profiles appear in a highlighted banner above the KPIs.</p></div>
      <div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div><h3>Face-Centred Profile Photos</h3><p>Profile images are tight face-centred crops with generous padding, 2-step Lanczos upscaling, CLAHE contrast enhancement, and unsharp masking — sharp even from blurry CCTV.</p></div>
      <div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg></div><h3>Longitudinal Tracking</h3><p>Re-identification across days and cameras with cosine similarity matching, building long-term profiles with trend charts and temporal gaze/attention history.</p></div>
    </div>
  </div></section>
  <div class="footer-bottom" style="padding:24px 48px;background:var(--bg);border-top:1px solid var(--border)">
    <div style="max-width:1400px;margin:0 auto;display:flex;justify-content:space-between;align-items:center">
      <div style="font-size:.8rem;color:var(--text-muted)">© 2026 Sentio Mind. All rights reserved.</div>
      <div style="display:flex;gap:20px"><span style="font-size:.8rem;color:var(--text-muted);cursor:pointer">Privacy</span><span style="font-size:.8rem;color:var(--text-muted);cursor:pointer">Terms</span><span style="font-size:.8rem;color:var(--text-muted);cursor:pointer">Security</span></div>
    </div>
  </div>
</div>

<!-- DASHBOARD -->
<div id="page-dashboard" class="page-section">
  <div class="dashboard-wrap">
    <div class="dash-topbar">
      <div><div class="dash-title">Overview Dashboard</div><div class="dash-sub" id="dashDateSub">No analysis run yet</div></div>
      <button class="btn btn-primary" id="runBtn" onclick="runAnalysis()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5,3 19,12 5,21"/></svg>
        Run Analysis
      </button>
    </div>
    <!-- PINNED PROFILES BANNER -->
    <div class="pinned-banner" id="pinnedBanner" style="display:none">
      <div class="pinned-banner-title">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
        📌 Pinned Profiles
      </div>
      <div class="pinned-grid" id="pinnedGrid"></div>
    </div>
    <div class="kpi-row" id="kpiRow">
      <div class="kpi-card"><div class="kpi-label">Total Persons</div><div class="kpi-num" id="kpiPersons">—</div><div class="kpi-meta" id="kpiPersonsMeta">Run analysis to populate</div></div>
      <div class="kpi-card"><div class="kpi-label">Avg Wellbeing</div><div class="kpi-num" id="kpiWell">—</div><div class="kpi-meta" id="kpiWellMeta">—</div></div>
      <div class="kpi-card"><div class="kpi-label">Avg Engagement</div><div class="kpi-num" id="kpiEng">—</div><div class="kpi-meta">Across all persons</div></div>
      <div class="kpi-card"><div class="kpi-label">Days Analyzed</div><div class="kpi-num" id="kpiDays">—</div><div class="kpi-meta" id="kpiDaysMeta">—</div></div>
      <div class="kpi-card" style="border-color:#fca5a5"><div class="kpi-label" style="color:var(--red)">⚠ Needs Monitoring</div><div class="kpi-num kpi-bad" id="kpiAtRisk">—</div><div class="kpi-meta" id="kpiAtRiskMeta">—</div></div>
    </div>
    <div class="content-card">
      <div class="content-card-header"><div class="content-card-title">Top Tracked Persons — School Analysis</div></div>
      <div class="content-card-body" id="topPersonsList">
        <div class="empty-state"><div class="empty-icon">👁️</div><div class="empty-title">No data yet</div><div class="empty-sub">Click Run Analysis to process footage</div></div>
      </div>
    </div>
  </div>
</div>

<!-- PROFILES -->
<div id="page-profiles" class="page-section">
  <div class="dashboard-wrap">
    <div class="dash-topbar">
      <div><div class="dash-title">Person Profiles</div><div class="dash-sub">Auto-generated from detected individuals</div></div>
    </div>
    <div id="profilesGrid">
      <div class="empty-state"><div class="empty-icon">👤</div><div class="empty-title">No profiles yet</div><div class="empty-sub">Run analysis to auto-create profiles</div></div>
    </div>
  </div>
</div>

<!-- TEMPORAL -->
<div id="page-temporal" class="page-section">
  <div class="dashboard-wrap">
    <div class="dash-topbar"><div><div class="dash-title">Temporal Analysis</div><div class="dash-sub">Trait &amp; wellbeing trends over time per person</div></div></div>
    <div style="margin-bottom:20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
      <label style="font-size:.82rem;font-weight:600;color:var(--text-secondary)">Person:</label>
      <select id="temporalPersonSelect" onchange="renderTemporalCharts()" style="padding:8px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface);font-size:.85rem;color:var(--text-primary);min-width:220px"><option value="">— run analysis first —</option></select>
      <label style="font-size:.82rem;font-weight:600;color:var(--text-secondary);margin-left:12px">Show:</label>
      <select id="temporalTraitSelect" onchange="renderTemporalCharts()" style="padding:8px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface);font-size:.85rem;color:var(--text-primary)">
        <option value="all">All Traits</option>
        <option value="wellbeing">Overall Wellbeing</option>
        <option value="emotional_positivity">Emotional Positivity</option>
        <option value="stress_resilience">Stress Resilience</option>
        <option value="social_engagement">Social Engagement</option>
        <option value="focus_alertness">Focus &amp; Alertness</option>
        <option value="physical_energy">Physical Energy</option>
        <option value="posture_health">Posture Health</option>
      </select>
    </div>
    <div id="temporalPersonCard" style="display:none;margin-bottom:20px;background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:20px;align-items:center;gap:20px">
      <img id="temporalAvatar" src="" style="width:80px;height:80px;border-radius:10px;object-fit:cover;border:2px solid var(--border)">
      <div><div id="temporalName" style="font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:800"></div><div id="temporalMeta" style="font-size:.8rem;color:var(--text-muted);margin-top:4px"></div><div id="temporalWbBadge" style="margin-top:8px"></div></div>
    </div>
    <div id="temporalChartsArea"><div class="empty-state"><div class="empty-icon">📈</div><div class="empty-title">Select a person above</div></div></div>
  </div>
</div>

<!-- DAILY -->
<div id="page-daily" class="page-section">
  <div class="dashboard-wrap">
    <div class="dash-topbar"><div><div class="dash-title">Daily Analysis</div><div class="dash-sub">Date-by-date breakdown</div></div></div>
    <div class="date-strip" id="dateStrip"></div>
    <div id="dailyContent"><div class="empty-state"><div class="empty-icon">📅</div><div class="empty-title">No daily data</div></div></div>
  </div>
</div>

<!-- TIMELINE -->
<div id="page-timeline" class="page-section">
  <div class="dashboard-wrap">
    <div class="dash-topbar"><div><div class="dash-title">Person Timeline</div><div class="dash-sub">Day-by-day appearance &amp; behavior stream</div></div></div>
    <div id="timelineContent"><div class="empty-state"><div class="empty-icon">⏱️</div><div class="empty-title">No timeline data</div></div></div>
  </div>
</div>

<!-- SETTINGS -->
<div id="page-settings" class="page-section">
  <div class="dashboard-wrap">
    <div class="dash-topbar"><div><div class="dash-title">System Settings</div><div class="dash-sub">Configuration and detection status</div></div></div>
    <div class="content-card">
      <div class="content-card-header"><div class="content-card-title">Detection Modules</div></div>
      <div class="content-card-body"><div class="settings-grid">
        <div class="settings-row"><span class="settings-key">MTCNN (best for low-res)</span><span class="settings-val" id="settingMtcnn">Checking…</span></div>
        <div class="settings-row"><span class="settings-key">DeepFace Emotions</span><span class="settings-val" id="settingDeepface">Checking…</span></div>
        <div class="settings-row"><span class="settings-key">MediaPipe Pose + Gaze</span><span class="settings-val" id="settingMediapipe">Checking…</span></div>
        <div class="settings-row"><span class="settings-key">face_recognition HOG</span><span class="settings-val" id="settingFaceRec">Checking…</span></div>
        <div class="settings-row"><span class="settings-key">Haar Cascade Fallback</span><span class="settings-val">✓ Always on</span></div>
        <div class="settings-row"><span class="settings-key">Multi-scale Upscale</span><span class="settings-val">2× Lanczos ✓</span></div>
        <div class="settings-row"><span class="settings-key">Similarity Threshold</span><span class="settings-val">48%</span></div>
        <div class="settings-row"><span class="settings-key">Max Frames/Video</span><span class="settings-val">12 keyframes</span></div>
        <div class="settings-row"><span class="settings-key">Profile Image</span><span class="settings-val">Face-centred 240×240</span></div>
        <div class="settings-row"><span class="settings-key">Parallel Face Analysis</span><span class="settings-val">ThreadPoolExecutor ✓</span></div>
      </div></div>
    </div>
    <div class="content-card" style="margin-top:20px">
      <div class="content-card-header"><div class="content-card-title">Folder Structure</div></div>
      <div class="content-card-body">
        <pre style="font-size:.85rem;line-height:1.8;color:var(--text-secondary);background:var(--bg);padding:20px;border-radius:var(--radius-sm);border:1px solid var(--border);overflow-x:auto">input_videos/
  Delhi_Public_School/
    CCTV_24_02_2026/
      camera1.mp4
    CCTV_25_02_2026/
      recording.avi</pre>
      </div>
    </div>
  </div>
</div>

<div class="loading-overlay" id="loadingOverlay">
  <div class="spinner"></div>
  <div class="loading-title">Analyzing footage…</div>
  <div class="loading-sub" id="loadingSub">This may take several minutes</div>
</div>

<div class="modal-overlay" id="editModal">
  <div class="modal">
    <h3>Edit Person Name</h3>
    <p>Update the display name. Saved to the profile database.</p>
    <input class="modal-input" id="modalNameInput" type="text" placeholder="Enter new name…"/>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="saveModalName()">Save</button>
    </div>
  </div>
</div>

<script>
/* ─── STATE ─── */
let currentData = {};
let editingPersonId = null;

/* ─── XSS-SAFE STRING HELPERS ───────────────────────────────────────────
   Person names/schools are user-editable (see /update_person_name), so
   they must never be interpolated into innerHTML or onclick="" strings
   unescaped. escHtml() is for plain HTML text nodes/attributes. escJs()
   must be applied FIRST for values embedded inside an inline onclick="'...'"
   JS string literal, then escHtml() around that (attribute HTML-decoding
   happens before the JS is parsed, so both layers are required). */
function escHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
    { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]
  ));
}
function escJs(s) {
  return String(s == null ? '' : s)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/</g, '\\x3C')
    .replace(/>/g, '\\x3E');
}

const TRAIT_COLORS = {
  emotional_positivity:'#f59e0b', stress_resilience:'#10b981', social_engagement:'#3b82f6',
  social_confidence:'#8b5cf6',    physical_energy:'#ef4444',   posture_health:'#06b6d4',
  body_openness:'#84cc16',        focus_alertness:'#f97316',   facial_relaxation:'#ec4899',
  vitality_glow:'#a78bfa',        wellbeing:'#2563eb'
};
const TRAIT_LABELS = {
  emotional_positivity:'😊 Emotional Positivity', stress_resilience:'🛡️ Stress Resilience',
  social_engagement:'🤝 Social Engagement',       social_confidence:'💬 Social Confidence',
  physical_energy:'⚡ Physical Energy',            posture_health:'🧍 Posture Health',
  body_openness:'🙌 Body Openness',               focus_alertness:'👁️ Focus & Alertness',
  facial_relaxation:'😌 Facial Relaxation',        vitality_glow:'✨ Vitality & Glow',
  wellbeing:'📊 Overall Wellbeing'
};
const ALL_TRAITS = Object.keys(TRAIT_COLORS).filter(k => k !== 'wellbeing');
let temporalChartInstances = {};
let dashMiniCharts = {};

/* ─── NAVIGATION ─── */
function goTo(page, el) {
  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  if (el) el.classList.add('active');
}
function goToAndAnalyze() {
  goTo('dashboard', document.querySelectorAll('.nav-link')[1]);
  setTimeout(runAnalysis, 200);
}

/* ─── ANALYSIS ─── */
async function runAnalysis() {
  document.getElementById('loadingOverlay').classList.add('active');
  document.getElementById('runBtn').disabled = true;
  document.getElementById('loadingSub').textContent = 'Running multi-scale detection + gaze analysis…';
  try {
    const r = await fetch('/run_analysis', { method: 'POST' });
    const d = await r.json();
    if (d.success) {
      currentData = d.report;
      renderAll(d.report);
      document.getElementById('dashDateSub').textContent = 'Last updated: ' + new Date().toLocaleString();
    } else { alert('Error: ' + d.message); }
  } catch(e) { alert('Error: ' + e); }
  finally {
    document.getElementById('loadingOverlay').classList.remove('active');
    document.getElementById('runBtn').disabled = false;
  }
}

function renderAll(report) {
  renderKPIs(report);
  renderPinnedBanner(report);
  renderTopPersons(report);
  renderProfiles(report);
  renderTemporalSetup(report);
  renderDaily(report);
  renderTimeline(report);
}

/* ─── GAZE VISUALISER ─── */
function gazeWidget(gaze) {
  if (!gaze) return '';
  const dir  = gaze.gaze_direction || 'forward';
  const attn = gaze.attention_score || 50;
  const zone = gaze.focus_zone || 'ahead';
  const ec   = gaze.eye_contact ? '👁️ Eye contact' : '';
  // Map gaze_horizontal / gaze_vertical (-1..+1) to CSS offset in the eye box
  const gh   = Math.max(-1, Math.min(1, gaze.gaze_horizontal || 0));
  const gv   = Math.max(-1, Math.min(1, gaze.gaze_vertical   || 0));
  const irisX = 50 + gh * 30;   // % left
  const irisY = 50 + gv * 30;   // % top
  const dirCls = ['forward','left','right','up','down','camera','distracted'].includes(dir)
                  ? 'gaze-' + dir : 'gaze-forward';
  const attnColor = attn >= 70 ? '#10b981' : attn >= 45 ? '#f59e0b' : '#ef4444';
  return `<div style="margin-top:10px;padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px">
    <div style="font-size:.65rem;font-weight:700;color:var(--text-muted);letter-spacing:.07em;text-transform:uppercase;margin-bottom:7px">👁️ Gaze & Attention</div>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
      <div class="gaze-eye-box">
        <div class="gaze-iris" style="left:calc(${irisX}% - 6px);top:calc(${irisY}% - 6px)"></div>
      </div>
      <div>
        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
          <span class="gaze-dir-badge ${dirCls}">${dir}</span>
          <span style="font-size:.7rem;color:var(--text-muted)">zone: <b>${zone}</b></span>
          ${ec ? '<span style="font-size:.7rem;color:var(--green)">'+ec+'</span>' : ''}
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-top:5px">
          <span style="font-size:.68rem;color:var(--text-muted)">Attention</span>
          <div style="width:70px;height:5px;background:var(--surface2);border-radius:3px;overflow:hidden">
            <div style="width:${attn}%;height:100%;background:${attnColor};border-radius:3px"></div>
          </div>
          <span style="font-size:.7rem;font-weight:700;color:${attnColor}">${attn}%</span>
        </div>
        ${gaze.head_yaw !== undefined ? `<div style="font-size:.65rem;color:var(--text-muted);margin-top:3px">Head: yaw ${gaze.head_yaw}° pitch ${gaze.head_pitch}°</div>` : ''}
      </div>
    </div>
  </div>`;
}

/* ─── PINNED BANNER ─── */
function renderPinnedBanner(report) {
  const pinned = report.pinned_profiles || [];
  const banner = document.getElementById('pinnedBanner');
  const grid   = document.getElementById('pinnedGrid');
  if (!pinned.length) { banner.style.display = 'none'; return; }
  banner.style.display = 'block';
  grid.innerHTML = pinned.map(pid => {
    const p = report.person_profiles[pid];
    if (!p) return '';
    const wc = p.average_wellbeing >= 70 ? '#10b981' : p.average_wellbeing >= 50 ? '#f59e0b' : '#ef4444';
    return `<div class="pinned-chip" onclick="goToPersonTemporal('${pid}')">
      <img src="data:image/jpeg;base64,${p.profile_image}" alt="">
      <div><div class="pinned-chip-name">${escHtml(p.name)}</div>
        <div class="pinned-chip-wb" style="color:${wc}">${p.average_wellbeing}%</div></div>
      <span class="unpin-btn" onclick="event.stopPropagation();unpinProfile('${pid}')" title="Unpin">✕</span>
    </div>`;
  }).join('');
}

/* ─── KPIs ─── */
function renderKPIs(report) {
  const stats   = report.overall_stats;
  const persons = Object.values(report.person_profiles);
  const avgW    = persons.length ? Math.round(persons.reduce((a,p)=>a+p.average_wellbeing,0)/persons.length) : 0;
  const avgE    = persons.length ? Math.round(persons.reduce((a,p)=>a+p.average_engagement,0)/persons.length) : 0;
  const atRisk  = persons.filter(p=>p.average_wellbeing<50).length;
  document.getElementById('kpiPersons').textContent     = stats.total_unique_persons;
  document.getElementById('kpiPersonsMeta').textContent = `${stats.total_schools||1} school(s), ${stats.total_dates_analyzed} day(s)`;
  document.getElementById('kpiWell').innerHTML          = `${avgW}<span class="kpi-unit">%</span>`;
  document.getElementById('kpiWellMeta').innerHTML      = `<span class="${avgW>=70?'kpi-good':avgW>=50?'kpi-warn':'kpi-bad'}">${avgW>=70?'↑ Good':avgW>=50?'→ Moderate':'↓ Needs attention'}</span>`;
  document.getElementById('kpiEng').innerHTML           = `${avgE}<span class="kpi-unit">%</span>`;
  document.getElementById('kpiDays').textContent        = stats.total_dates_analyzed;
  document.getElementById('kpiDaysMeta').textContent    = `${stats.date_range[0]||''} → ${stats.date_range.at(-1)||''}`;
  document.getElementById('kpiAtRisk').textContent      = atRisk;
  document.getElementById('kpiAtRiskMeta').textContent  = 'Wellbeing below 50%';
}

/* ─── TOP PERSONS ─── */
let dashMiniChartStore = {};
function destroyDashMini() {
  Object.values(dashMiniChartStore).forEach(c=>{try{c.destroy()}catch(e){}});
  dashMiniChartStore = {};
}
function renderTopPersons(report) {
  destroyDashMini();
  const allPersons = Object.values(report.person_profiles);
  const schools    = report.overall_stats.schools || [];
  let html = '';
  schools.forEach(school => {
    const sp     = allPersons.filter(p => p.school === school);
    if (!sp.length) return;
    const avgW   = Math.round(sp.reduce((a,p)=>a+p.average_wellbeing,0)/sp.length);
    const atRisk = sp.filter(p=>p.average_wellbeing<50).sort((a,b)=>a.average_wellbeing-b.average_wellbeing);
    const top4   = [...sp].sort((a,b)=>b.total_detections-a.total_detections).slice(0,4);
    const sc     = avgW>=70?'var(--green)':avgW>=50?'var(--amber)':'var(--red)';

    html += `<div style="background:var(--surface);border:1px solid var(--border);border-radius:16px;margin-bottom:24px;overflow:hidden">
      <div style="padding:20px 24px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--bg)">
        <div><div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800">${school}</div>
          <div style="font-size:.8rem;color:var(--text-muted)">${sp.length} persons · ${atRisk.length} monitoring</div></div>
        <div style="text-align:right"><div style="font-family:'Syne',sans-serif;font-size:1.75rem;font-weight:800;color:${sc}">${avgW}%</div>
          <div style="font-size:.65rem;color:var(--text-muted);font-weight:600;letter-spacing:.05em">AVG WELLBEING</div></div>
      </div>`;

    if (atRisk.length) {
      html += `<div style="padding:14px 24px;border-bottom:1px solid var(--border);background:#fff8f8">
        <div style="font-size:.7rem;font-weight:700;color:var(--red);letter-spacing:.07em;text-transform:uppercase;margin-bottom:8px">⚠ Needs Monitoring</div>
        <div style="display:flex;flex-direction:column;gap:6px">`;
      atRisk.slice(0,5).forEach(p => {
        const lowest = p.avg_traits ? Object.entries(p.avg_traits).sort((a,b)=>a[1]-b[1])[0] : null;
        const gazeIcon = {forward:'→',left:'←',right:'→',up:'↑',down:'↓'}[p.dominant_gaze||'forward']||'→';
        html += `<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;background:white;border:1px solid #fca5a5;border-radius:8px">
          <img src="data:image/jpeg;base64,${p.profile_image}" style="width:38px;height:38px;border-radius:6px;object-fit:cover;flex-shrink:0">
          <div style="flex:1;min-width:0">
            <div style="font-weight:600;font-size:.85rem">${escHtml(p.name)}</div>
            <div style="font-size:.7rem;color:var(--text-muted)">Lowest: ${lowest?lowest[0].replace(/_/g,' '):'—'} (${lowest?lowest[1]:'—'}%) · Gaze: ${gazeIcon} ${p.dominant_gaze||'unknown'}</div>
          </div>
          <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800;color:var(--red)">${p.average_wellbeing}%</div>
        </div>`;
      });
      html += `</div></div>`;
    }

    html += `<div style="padding:16px 24px">
      <div style="font-size:.7rem;font-weight:700;color:var(--text-muted);letter-spacing:.07em;text-transform:uppercase;margin-bottom:10px">Top Tracked — Wellbeing Over Time</div>
      <div style="display:flex;flex-direction:column;gap:12px">`;
    top4.forEach(p => {
      const wc  = p.average_wellbeing>=70?'#10b981':p.average_wellbeing>=50?'#f59e0b':'#ef4444';
      const cid = 'mini_' + p.person_id.replace(/[^a-zA-Z0-9]/g,'_');
      const isPinned = (currentData.pinned_profiles||[]).includes(p.person_id);
      html += `<div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 14px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
          <img src="data:image/jpeg;base64,${p.profile_image}" style="width:44px;height:44px;border-radius:8px;object-fit:cover;border:2px solid var(--border);flex-shrink:0">
          <div style="flex:1;min-width:0">
            <div style="font-weight:700;font-size:.875rem">${escHtml(p.name)}</div>
            <div style="font-size:.7rem;color:var(--text-muted)">${p.total_detections} det · ${p.days_present}d · Gaze: ${p.dominant_gaze||'—'} · <span style="color:${wc};font-weight:700">${p.average_wellbeing}%</span></div>
          </div>
          <button onclick="goToPersonTemporal('${p.person_id}')" style="font-size:.7rem;padding:4px 8px;border:1px solid var(--accent);border-radius:6px;background:var(--accent-light);color:var(--accent);cursor:pointer;font-weight:600">Chart →</button>
          <button onclick="togglePin('${p.person_id}')" style="font-size:.7rem;padding:4px 8px;border:1px solid #c4b5fd;border-radius:6px;background:var(--pin-light);color:var(--pin);cursor:pointer;font-weight:600" id="pinbtn_${p.person_id.replace(/[^a-zA-Z0-9]/g,'_')}">${isPinned?'📌 Unpin':'📌 Pin'}</button>
        </div>
        <div style="position:relative;height:60px"><canvas id="${cid}"></canvas></div>
        <div style="font-size:.65rem;color:var(--text-muted);text-align:center;margin-top:3px">Wellbeing over time</div>
      </div>`;
    });
    html += `</div></div></div>`;
  });

  document.getElementById('topPersonsList').innerHTML = html ||
    '<div class="empty-state"><div class="empty-icon">👁️</div><div class="empty-title">No data</div></div>';

  setTimeout(() => {
    schools.forEach(school => {
      const sp = allPersons.filter(p=>p.school===school);
      [...sp].sort((a,b)=>b.total_detections-a.total_detections).slice(0,4).forEach(p => {
        const cid = 'mini_' + p.person_id.replace(/[^a-zA-Z0-9]/g,'_');
        if (p.temporal_series?.length) buildDashMini(cid, p.temporal_series);
      });
    });
  }, 120);
}

function buildDashMini(cid, series) {
  const ctx = document.getElementById(cid);
  if (!ctx) return;
  if (dashMiniChartStore[cid]) { try { dashMiniChartStore[cid].destroy(); } catch(e){} }
  const byDate = {};
  series.forEach(pt => { if (!byDate[pt.date]) byDate[pt.date]=[]; byDate[pt.date].push(pt.wellbeing); });
  const dates = Object.keys(byDate).sort();
  const vals  = dates.map(d => Math.round(byDate[d].reduce((a,v)=>a+v,0)/byDate[d].length));
  dashMiniChartStore[cid] = new Chart(ctx.getContext('2d'), {
    type:'line',
    data:{ labels: dates.length>1?dates:series.map((_,i)=>i+1+''), datasets:[{
      data: dates.length>1?vals:series.map(pt=>pt.wellbeing),
      borderColor:'#2563eb', backgroundColor:'#2563eb22', borderWidth:2, pointRadius:3, tension:.4, fill:true
    }]},
    options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}, scales:{x:{display:false},y:{display:false,min:0,max:100}} }
  });
}

/* ─── PROFILES PAGE ─── */
function renderProfiles(report) {
  const persons = Object.values(report.person_profiles).sort((a,b)=>b.total_detections-a.total_detections);
  if (!persons.length) { document.getElementById('profilesGrid').innerHTML='<div class="empty-state"><div class="empty-icon">👤</div><div class="empty-title">No profiles</div></div>'; return; }
  const schools = [...new Set(persons.map(p=>p.school||'Unknown'))].sort();
  let html = '';
  schools.forEach(school => {
    const sp   = persons.filter(p=>(p.school||'Unknown')===school);
    const avgW = Math.round(sp.reduce((a,p)=>a+p.average_wellbeing,0)/sp.length);
    const sc   = avgW>=70?'var(--green)':avgW>=50?'var(--amber)':'var(--red)';
    html += `<div style="margin-bottom:40px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid var(--border)">
        <div style="font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:800">${school}</div>
        <div style="display:flex;align-items:center;gap:16px">
          <span style="font-size:.8rem;color:var(--text-muted)">${sp.length} persons</span>
          <span style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:800;color:${sc}">${avgW}% avg wellbeing</span>
        </div>
      </div>
      <div class="person-grid">`;

    sp.forEach(p => {
      const isPinned = (report.pinned_profiles||[]).includes(p.person_id);
      const wc  = p.average_wellbeing>=70?'var(--green)':p.average_wellbeing>=50?'var(--amber)':'var(--red)';
      const cc  = p.average_wellbeing<40?'flagged':p.average_wellbeing<60?'warn':'';
      const pc  = isPinned ? 'pinned-card' : '';
      const wfc = p.average_wellbeing>=70?'well-high':p.average_wellbeing>=50?'well-mid':'well-low';
      const engTag = p.average_engagement>=60?'tag-green':p.average_engagement>=40?'tag-amber':'tag-red';
      const traits = p.avg_traits || {};
      const gaze   = p.temporal_series?.length ? (p.temporal_series.at(-1)||{}).gaze : p.dominant_gaze;
      const lastPt = p.temporal_series?.at(-1) || {};

      let traitsHtml = '';
      Object.keys(TRAIT_LABELS).filter(k=>k!=='wellbeing').forEach(tk => {
        const val = traits[tk] !== undefined ? traits[tk] : 50;
        const bc  = val>=70?'#10b981':val>=45?'#f59e0b':'#ef4444';
        traitsHtml += `<div style="margin-bottom:6px">
          <div style="display:flex;justify-content:space-between;margin-bottom:2px">
            <span style="font-size:.69rem;color:var(--text-secondary);font-weight:500">${TRAIT_LABELS[tk]}</span>
            <span style="font-size:.69rem;font-weight:700;color:${bc}">${val}%</span>
          </div>
          <div style="width:100%;height:4px;background:var(--surface2);border-radius:2px;overflow:hidden">
            <div style="width:${val}%;height:100%;background:${bc};border-radius:2px"></div>
          </div>
        </div>`;
      });

      html += `<div class="person-card ${cc} ${pc}" style="padding:0;overflow:hidden">
        <!-- Face-centred profile photo -->
        <div style="position:relative;width:100%;background:var(--surface2)">
          <img src="data:image/jpeg;base64,${p.profile_image}" id="avatar-${p.person_id}"
            style="width:100%;height:240px;object-fit:cover;object-position:top center;display:block;image-rendering:-webkit-optimize-contrast">
          <!-- Pin button -->
          <button onclick="togglePin('${p.person_id}')" title="${isPinned?'Unpin from dashboard':'Pin to dashboard'}"
            style="position:absolute;top:10px;left:10px;padding:5px 10px;background:${isPinned?'#7c3aed':'rgba(255,255,255,.9)'};border-radius:8px;border:${isPinned?'none':'1px solid #c4b5fd'};cursor:pointer;font-size:.68rem;font-weight:700;color:${isPinned?'white':'var(--pin)'};backdrop-filter:blur(4px);display:flex;align-items:center;gap:4px"
            id="pinbtn_card_${p.person_id.replace(/[^a-zA-Z0-9]/g,'_')}">
            📌 ${isPinned?'Pinned':'Pin'}
          </button>
          <!-- Upload photo -->
          <label style="position:absolute;top:10px;right:42px;width:30px;height:30px;background:rgba(37,99,235,.88);border-radius:8px;display:flex;align-items:center;justify-content:center;cursor:pointer;border:2px solid white">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <input type="file" accept="image/*" style="display:none" onchange="uploadPhoto(event,'${p.person_id}')">
          </label>
          <!-- Delete -->
          <button onclick="deletePerson('${p.person_id}','${escHtml(escJs(p.name))}')"
            style="position:absolute;top:10px;right:10px;width:30px;height:30px;background:rgba(220,38,38,.88);border-radius:8px;border:2px solid white;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
          </button>
          <!-- Wellbeing badge -->
          <div style="position:absolute;bottom:10px;left:10px;background:rgba(255,255,255,.92);border-radius:8px;padding:4px 10px;backdrop-filter:blur(4px)">
            <span style="font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:800;color:${wc}">${p.average_wellbeing}%</span>
            <span style="font-size:.62rem;color:var(--text-muted);font-weight:600;margin-left:3px">WELLBEING</span>
          </div>
          ${isPinned ? '<div style="position:absolute;bottom:10px;right:10px;background:#7c3aed;color:white;border-radius:6px;padding:3px 8px;font-size:.65rem;font-weight:700">📌 PINNED</div>' : ''}
        </div>
        <!-- Info section -->
        <div style="padding:14px 16px">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:6px">
            <div style="flex:1;min-width:0">
              <div class="person-name" onclick="openModal('${p.person_id}','${escHtml(escJs(p.name))}')">
                ${escHtml(p.name)}
                <svg style="display:inline;vertical-align:middle;margin-left:4px" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </div>
              <div style="font-size:.7rem;color:var(--text-muted)">${p.person_id}</div>
            </div>
          </div>
          <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:8px">
            <span class="tag tag-blue">${p.days_present}d tracked</span>
            <span class="tag ${engTag}">${p.average_engagement}% eng</span>
            <span class="tag tag-blue">${p.total_detections} det</span>
            ${isPinned?'<span class="tag tag-pin">📌 Pinned</span>':''}
          </div>
          <div class="well-track"><div class="well-fill ${wfc}" style="width:${p.average_wellbeing}%"></div></div>
          <!-- GAZE WIDGET -->
          ${gazeWidget({ gaze_direction: gaze||p.dominant_gaze, attention_score: lastPt.attention||50, focus_zone: lastPt.focus_zone||'ahead', gaze_horizontal:0, gaze_vertical:0, head_yaw: 0, head_pitch: 0 })}
          <!-- 10-trait bars -->
          <div style="margin-top:12px">
            <div style="font-size:.66rem;font-weight:700;color:var(--text-muted);letter-spacing:.07em;text-transform:uppercase;margin-bottom:7px">10-Trait Behavioral Analysis</div>
            ${traitsHtml}
          </div>
          <div style="margin-top:10px">
            <div class="metric-item"><span class="metric-k">First Seen</span><span class="metric-v">${p.dates_seen[0]||'—'}</span></div>
            <div class="metric-item"><span class="metric-k">Last Seen</span><span class="metric-v">${p.dates_seen.at(-1)||'—'}</span></div>
            <div class="metric-item"><span class="metric-k">Dominant Gaze</span><span class="metric-v">${p.dominant_gaze||'—'}</span></div>
          </div>
        </div>
      </div>`;
    });
    html += `</div></div>`;
  });
  document.getElementById('profilesGrid').innerHTML = html;
}

/* ─── PIN / UNPIN ─── */
async function togglePin(personId) {
  const pinned = currentData.pinned_profiles || [];
  const isPinned = pinned.includes(personId);
  const action = isPinned ? 'unpin' : 'pin';
  try {
    const r = await fetch('/pin_profile', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ person_id: personId, action }) });
    const d = await r.json();
    if (d.success) {
      if (isPinned) { currentData.pinned_profiles = pinned.filter(p=>p!==personId); }
      else          { currentData.pinned_profiles = [...pinned, personId]; }
      if (currentData.person_profiles?.[personId]) {
        currentData.person_profiles[personId].pinned = !isPinned;
      }
      renderAll(currentData);
    }
  } catch(e) { console.error('Pin error:', e); }
}
async function unpinProfile(personId) { await togglePin(personId); }

/* ─── TEMPORAL PAGE ─── */
function renderTemporalSetup(report) {
  const sel = document.getElementById('temporalPersonSelect');
  const persons = Object.values(report.person_profiles).sort((a,b)=>b.total_detections-a.total_detections);
  sel.innerHTML = '<option value="">— select a person —</option>';
  persons.forEach(p => {
    const o = document.createElement('option');
    o.value = p.person_id;
    o.textContent = `${p.name} (${p.school||''}) · ${p.total_detections} det`;
    sel.appendChild(o);
  });
}

function destroyTemporalCharts() {
  Object.values(temporalChartInstances).forEach(c=>{try{c.destroy()}catch(e){}});
  temporalChartInstances = {};
}
function makeDS(key, data, fill=false) {
  const color = TRAIT_COLORS[key]||'#64748b';
  return { label: TRAIT_LABELS[key]||key, data, borderColor:color, backgroundColor:color+'18', borderWidth:fill?3:2, pointRadius:4, pointHoverRadius:6, tension:.4, fill };
}
function buildChart(parentEl, id, title, labels, datasets) {
  const wrap = document.createElement('div');
  wrap.style.cssText = 'background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin-bottom:14px';
  wrap.innerHTML = `<div style="font-size:.88rem;font-weight:700;margin-bottom:12px">${title}</div><div style="position:relative;height:200px"><canvas id="c_${id}"></canvas></div>`;
  parentEl.appendChild(wrap);
  const ctx = document.getElementById('c_'+id);
  if (!ctx) return;
  temporalChartInstances['c_'+id] = new Chart(ctx.getContext('2d'), {
    type:'line', data:{labels, datasets},
    options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
      plugins:{legend:{position:'top',labels:{font:{family:'DM Sans',size:11},boxWidth:12,padding:8}},
        tooltip:{callbacks:{label:c=>' '+(c.dataset.label||'')+': '+(c.parsed.y??'—')+'%'}}},
      scales:{x:{title:{display:true,text:'Time (s)'},ticks:{font:{size:10},maxRotation:30},grid:{color:'#f0eeea'}},
              y:{min:0,max:100,title:{display:true,text:'Score (%)'},ticks:{font:{size:10}},grid:{color:'#f0eeea'}}}}
  });
}
function renderTemporalCharts() {
  if (!currentData) return;
  const pid  = document.getElementById('temporalPersonSelect').value;
  const mode = document.getElementById('temporalTraitSelect').value;
  const area = document.getElementById('temporalChartsArea');
  if (!pid) { area.innerHTML='<div class="empty-state"><div class="empty-icon">👤</div><div class="empty-title">Select a person</div></div>'; return; }
  const p = currentData.person_profiles[pid];
  if (!p) return;

  const card = document.getElementById('temporalPersonCard');
  card.style.display = 'flex';
  document.getElementById('temporalAvatar').src = 'data:image/jpeg;base64,'+p.profile_image;
  document.getElementById('temporalName').textContent = p.name;
  document.getElementById('temporalMeta').textContent = `${p.school||''} · ${p.total_detections} detections · ${p.days_present} days`;
  const wbColor = p.average_wellbeing>=70?'#10b981':p.average_wellbeing>=50?'#f59e0b':'#ef4444';
  document.getElementById('temporalWbBadge').innerHTML = `<span style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;color:${wbColor}">${p.average_wellbeing}%</span><span style="font-size:.75rem;color:var(--text-muted);margin-left:6px">avg wellbeing</span>`;

  const series = p.temporal_series||[];
  if (!series.length) { area.innerHTML='<div class="empty-state"><div class="empty-icon">📉</div><div class="empty-title">No temporal data</div></div>'; return; }

  destroyTemporalCharts();
  area.innerHTML = '';

  const byDate = {};
  series.forEach(pt=>{ if (!byDate[pt.date]) byDate[pt.date]=[]; byDate[pt.date].push(pt); });
  const dates = Object.keys(byDate).sort();

  dates.forEach(date => {
    const pts  = byDate[date].sort((a,b)=>a.t-b.t);
    const xLbs = pts.map(pt=>pt.t.toFixed(1)+'s');
    const dayDiv = document.createElement('div');
    dayDiv.style.cssText = 'margin-bottom:28px';
    dayDiv.innerHTML = `<div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1rem;padding:10px 0 8px;border-bottom:2px solid var(--border);margin-bottom:14px;display:flex;align-items:center;gap:10px">
      <span style="background:var(--accent);color:white;border-radius:6px;padding:2px 10px;font-size:.8rem">${date}</span>
      <span style="font-size:.8rem;font-weight:400;color:var(--text-muted)">${pts.length} pts · ${pts[0].video||''}</span>
    </div>`;
    area.appendChild(dayDiv);

    if (mode === 'all') {
      buildChart(dayDiv,'wb_'+date+'_'+pid,'Overall Wellbeing — '+date, xLbs, [makeDS('wellbeing',pts.map(pt=>pt.wellbeing),true)]);
      buildChart(dayDiv,'emo_'+date+'_'+pid,'Emotional & Social — '+date, xLbs,
        ['emotional_positivity','stress_resilience','social_engagement','social_confidence','focus_alertness'].map(tk=>makeDS(tk,pts.map(pt=>pt.traits[tk]??null))));
      buildChart(dayDiv,'phy_'+date+'_'+pid,'Physical & Appearance — '+date, xLbs,
        ['physical_energy','posture_health','body_openness','facial_relaxation','vitality_glow'].map(tk=>makeDS(tk,pts.map(pt=>pt.traits[tk]??null))));
      // Attention / gaze chart
      buildChart(dayDiv,'gaze_'+date+'_'+pid,'Attention Score — '+date, xLbs,
        [{ label:'Attention Score', data: pts.map(pt=>pt.attention||50), borderColor:'#7c3aed', backgroundColor:'#7c3aed18', borderWidth:2, pointRadius:4, tension:.4, fill:true }]);
    } else {
      const ds = mode==='wellbeing' ? [makeDS('wellbeing',pts.map(pt=>pt.wellbeing),true)] :
                 [makeDS(mode,pts.map(pt=>pt.traits[mode]??null))];
      buildChart(dayDiv,mode+'_'+date+'_'+pid,(TRAIT_LABELS[mode]||mode)+' — '+date, xLbs, ds);
    }
  });
}
function goToPersonTemporal(pid) {
  goTo('temporal', document.querySelectorAll('.nav-link')[3]);
  setTimeout(()=>{ const sel=document.getElementById('temporalPersonSelect'); if(sel){sel.value=pid;renderTemporalCharts();} },150);
}

/* ─── DAILY ─── */
function renderDaily(report) {
  const dates = report.overall_stats.date_range;
  if (!dates.length) return;
  document.getElementById('dateStrip').innerHTML = dates.map((d,i)=>`<div class="date-pill ${i===0?'active':''}" onclick="selectDate('${d}',this)">${d}</div>`).join('');
  showDate(dates[0], report);
}
function selectDate(date, el) {
  document.querySelectorAll('.date-pill').forEach(p=>p.classList.remove('active'));
  el.classList.add('active');
  showDate(date, currentData);
}
function showDate(date, report) {
  const dd = report.date_summaries[date] || Object.values(report.date_summaries).find(d=>d.date===date);
  if (!dd) return;
  const html = `<div class="kpi-row">
    <div class="kpi-card"><div class="kpi-label">Unique Persons</div><div class="kpi-num">${dd.summary.unique_persons}</div></div>
    <div class="kpi-card"><div class="kpi-label">Avg Wellbeing</div><div class="kpi-num">${dd.summary.average_wellbeing}<span class="kpi-unit">%</span></div></div>
    <div class="kpi-card"><div class="kpi-label">Total Detections</div><div class="kpi-num">${dd.summary.total_detections}</div></div>
    <div class="kpi-card"><div class="kpi-label">Videos</div><div class="kpi-num">${dd.videos.length}</div></div>
  </div>
  <div class="content-card"><div class="content-card-header"><div class="content-card-title">Videos on ${date}</div></div>
    <div class="content-card-body">
      ${dd.videos.map(v=>`<div style="padding:12px 16px;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-sm);margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
        <span style="font-weight:600;font-size:.875rem">${v.video_name}</span>
        <span style="font-size:.8rem;color:var(--text-muted)">${v.total_frames_analyzed} frames</span>
      </div>`).join('')}
    </div>
  </div>`;
  document.getElementById('dailyContent').innerHTML = html;
}

/* ─── TIMELINE ─── */
function renderTimeline(report) {
  const persons = Object.values(report.person_profiles).sort((a,b)=>b.total_detections-a.total_detections);
  if (!persons.length) return;
  let html = '<div class="timeline-stream">';
  persons.forEach(p => {
    p.dates_seen.forEach((date,i) => {
      const last = i===p.dates_seen.length-1;
      html += `<div class="tl-item">
        <div style="display:flex;flex-direction:column;align-items:center;padding-top:4px">
          <div class="tl-dot"></div>${!last?'<div class="tl-line"></div>':''}
        </div>
        <div class="tl-body">
          <div class="tl-date">${date}</div>
          <div class="tl-person">${escHtml(p.name)}${(report.pinned_profiles||[]).includes(p.person_id)?' 📌':''}</div>
          <div class="tl-meta">${p.school||''} · ${p.person_id} · Wellbeing ${p.average_wellbeing}% · Gaze: ${p.dominant_gaze||'—'}</div>
        </div>
      </div>`;
    });
  });
  html += '</div>';
  document.getElementById('timelineContent').innerHTML = html;
}

/* ─── PROFILE ACTIONS ─── */
async function deletePerson(personId, personName) {
  if (!confirm(`Delete "${personName}"? Cannot be undone.`)) return;
  const r = await fetch('/delete_person', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({person_id:personId}) });
  const d = await r.json();
  if (d.success) { delete currentData.person_profiles[personId]; currentData.pinned_profiles=(currentData.pinned_profiles||[]).filter(p=>p!==personId); renderAll(currentData); }
  else alert('Error: '+d.message);
}
async function uploadPhoto(event, personId) {
  const file = event.target.files[0]; if (!file) return;
  const reader = new FileReader();
  reader.onload = async e => {
    const b64 = e.target.result.split(',')[1];
    const r = await fetch('/update_person_photo', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({person_id:personId,image_b64:b64}) });
    const d = await r.json();
    if (d.success) {
      const img = document.getElementById('avatar-'+personId);
      if (img) img.src = e.target.result;
      if (currentData.person_profiles?.[personId]) currentData.person_profiles[personId].profile_image = b64;
    }
  };
  reader.readAsDataURL(file);
}
function openModal(personId, currentName) {
  editingPersonId = personId;
  document.getElementById('modalNameInput').value = currentName;
  document.getElementById('editModal').classList.add('active');
  setTimeout(()=>document.getElementById('modalNameInput').focus(),100);
}
function closeModal() { document.getElementById('editModal').classList.remove('active'); editingPersonId=null; }
async function saveModalName() {
  const name = document.getElementById('modalNameInput').value.trim();
  if (!name || !editingPersonId) return;
  const r = await fetch('/update_person_name', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({person_id:editingPersonId,name}) });
  const d = await r.json();
  if (d.success) {
    if (currentData.person_profiles?.[editingPersonId]) currentData.person_profiles[editingPersonId].name = name;
    renderAll(currentData); closeModal();
  }
}
document.getElementById('editModal').addEventListener('click', e=>{ if(e.target===document.getElementById('editModal'))closeModal(); });
document.getElementById('modalNameInput').addEventListener('keydown', e=>{ if(e.key==='Enter')saveModalName(); if(e.key==='Escape')closeModal(); });

/* ─── INIT ─── */
async function loadSystemInfo() {
  try {
    const d = await (await fetch('/system_info')).json();
    document.getElementById('settingMtcnn').textContent      = d.mtcnn          ? '✓ Available (best quality)' : '✗ pip install mtcnn';
    document.getElementById('settingDeepface').textContent   = d.deepface       ? '✓ Available' : '✗ Not installed';
    document.getElementById('settingMediapipe').textContent  = d.mediapipe      ? '✓ Available' : '✗ Not installed';
    document.getElementById('settingFaceRec').textContent    = d.face_recognition?'✓ Available' : '✗ Not installed';
  } catch(e) {}
}
async function loadExistingData() {
  try {
    const d = await (await fetch('/get_report')).json();
    if (d.success && d.report) { currentData=d.report; renderAll(d.report); document.getElementById('dashDateSub').textContent='Loaded from saved report'; }
  } catch(e) {}
}
loadSystemInfo(); loadExistingData();
</script>
</body>
</html>'''
