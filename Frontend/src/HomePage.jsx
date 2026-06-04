//VERSION 1

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "./context/SessionContext";
import { getDashboardPathForUser } from "./utils/roleRoutes";
import hope from "./assets/hope.jpg";
import logo from "./assets/logo.png";

function LoadingScreen() {
  return (
    <div style={{
      height: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", background: "#111",
      color: "#fff", fontFamily: "sans-serif", fontSize: 16, gap: 12,
    }}>
      <span style={{
        width: 18, height: 18, border: "2px solid rgba(255,255,255,0.2)",
        borderTopColor: "#fff", borderRadius: "50%",
        animation: "spin 0.7s linear infinite", display: "inline-block",
      }} />
      Authenticating…
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export default function HomePage() {
  const { isAuthenticated, initializing, loginWithCredentials, user } = useSession();

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [showPass, setShowPass] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (!initializing && isAuthenticated && user) {
      navigate(getDashboardPathForUser(user), { replace: true });
    }
  }, [initializing, isAuthenticated, user, navigate]);

  if (initializing) return <LoadingScreen />;
  if (isAuthenticated) return <LoadingScreen />;

  async function handleSignIn(e) {
    e.preventDefault();
    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const { dashboardPath } = await loginWithCredentials(email.trim(), password, remember);
      navigate(dashboardPath, { replace: true });
    } catch (err) {
      setError(err.message || "Sign in failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html, body, #root { height: 100%; }

        /* ── Headline gradient: light aqua → light teal, very bright ── */
        .cta-gradient-text {
          background: linear-gradient(90deg, #7ffff4, #a0f0e8);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .lp-root {
          position: relative;
          height: 100vh;
          width: 100vw;
          overflow: hidden;
          font-family: 'Inter', sans-serif;
          display: flex;
          align-items: center;
        }

        .lp-bg {
          position: absolute;
          inset: 0;
          background-size: cover;
          background-position: center;
        }

        /* Slightly darker overlay for stronger text contrast */
        .lp-overlay {
          position: absolute;
          inset: 0;
          background: rgba(0, 0, 0, 0.42);
        }

        .lp-layout {
          position: relative;
          z-index: 2;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 6%;
          gap: 40px;
        }

        /* ── LEFT ── */
        .lp-left {
          flex: 1;
          color: #fff;
          max-width: 560px;
        }

        .lp-headline {
          font-size: clamp(42px, 5vw, 68px);
          font-weight: 800;
          line-height: 1.10;
          color: #fff;
          margin-bottom: 26px;
          letter-spacing: -0.5px;
          text-shadow: 0 2px 16px rgba(0,0,0,0.45);
        }

        .lp-sub {
          font-size: clamp(15px, 1.4vw, 18px);
          line-height: 1.80;
          color: rgba(255,255,255,0.92);
          max-width: 440px;
          font-weight: 400;
          margin-bottom: 40px;
          text-shadow: 0 1px 8px rgba(0,0,0,0.5);
        }

        .lp-socials {
          display: flex;
          gap: 14px;
          align-items: center;
        }

        .lp-social {
          width: 40px; height: 40px;
          display: flex; align-items: center; justify-content: center;
          border-radius: 10px;
          background: rgba(255,255,255,0.15);
          border: 1px solid rgba(255,255,255,0.22);
          text-decoration: none;
          transition: background 0.18s, transform 0.18s;
        }
        .lp-social:hover {
          background: rgba(255,255,255,0.28);
          transform: translateY(-2px);
        }
        .lp-social svg { width: 19px; height: 19px; }

        /* ── RIGHT: card — wider, bigger, takes more screen ── */
        .lp-card {
          width: 420px;
          flex-shrink: 0;
          background: rgba(28, 30, 38, 0.82);
          backdrop-filter: blur(28px);
          -webkit-backdrop-filter: blur(28px);
          border-radius: 20px;
          border: 1px solid rgba(255,255,255,0.12);
          padding: 44px 40px 38px;
          color: #fff;
        }

        .lp-card-title {
          font-size: 24px;
          font-weight: 700;
          color: #fff;
          margin-bottom: 6px;
          letter-spacing: -0.2px;
        }

        .lp-card-sub {
          font-size: 14px;
          color: rgba(255,255,255,0.50);
          margin-bottom: 28px;
          font-weight: 400;
        }

        .lp-oauth-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-bottom: 24px;
        }

        .lp-oauth-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 9px;
          padding: 12px 0;
          border-radius: 10px;
          border: 1px solid rgba(255,255,255,0.14);
          background: rgba(255,255,255,0.09);
          color: rgba(255,255,255,0.88);
          font-size: 14px;
          font-family: 'Inter', sans-serif;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.18s;
        }
        .lp-oauth-btn:hover { background: rgba(255,255,255,0.16); }

        .lp-divider {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 12px;
          color: rgba(255,255,255,0.35);
          letter-spacing: 0.5px;
          margin-bottom: 20px;
        }
        .lp-divider::before, .lp-divider::after {
          content: '';
          flex: 1;
          height: 1px;
          background: rgba(255,255,255,0.14);
        }

        .lp-field {
          position: relative;
          margin-bottom: 14px;
        }

        .lp-field-logo {
          position: absolute;
          left: 14px;
          top: 50%;
          transform: translateY(-50%);
          color: rgba(255,255,255,0.38);
          display: flex;
          pointer-events: none;
        }

        .lp-input {
          width: 100%;
          padding: 13px 44px 13px 42px;
          background: rgba(255,255,255,0.09);
          border: 1px solid rgba(255,255,255,0.14);
          border-radius: 10px;
          color: #fff;
          font-size: 15px;
          font-family: 'Inter', sans-serif;
          outline: none;
          transition: border-color 0.18s, background 0.18s;
        }
        .lp-input::placeholder { color: rgba(255,255,255,0.38); }
        .lp-input:focus {
          border-color: rgba(61, 214, 208, 0.5);
          background: rgba(255,255,255,0.12);
        }

        .lp-eye-btn {
          position: absolute;
          right: 13px;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          cursor: pointer;
          color: rgba(255,255,255,0.38);
          display: flex;
          padding: 2px;
          transition: color 0.15s;
        }
        .lp-eye-btn:hover { color: rgba(255,255,255,0.72); }

        .lp-meta {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 20px;
          margin-top: 2px;
        }

        .lp-remember {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: rgba(255,255,255,0.55);
          cursor: pointer;
          user-select: none;
        }

        .lp-remember input[type=checkbox] {
          width: 14px; height: 14px;
          accent-color: #3dd6d0;
          cursor: pointer;
        }

        .lp-forgot {
          font-size: 13px;
          color: #7ad4ff;
          text-decoration: none;
          transition: color 0.15s;
        }
        .lp-forgot:hover { color: #b8e8ff; text-decoration: underline; }

        .lp-error {
          font-size: 13px;
          color: #ff9090;
          background: rgba(255,60,60,0.10);
          border: 1px solid rgba(255,60,60,0.22);
          border-radius: 9px;
          padding: 10px 14px;
          margin-bottom: 16px;
          line-height: 1.5;
        }

        .lp-btn {
          width: 100%;
          padding: 14px;
          background: linear-gradient(135deg, #4a8a94 0%, #3dd6d0 100%);
          border: none;
          border-radius: 10px;
          color: #fff;
          font-size: 15px;
          font-weight: 600;
          font-family: 'Inter', sans-serif;
          cursor: pointer;
          transition: opacity 0.18s, transform 0.12s;
          margin-bottom: 18px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }
        .lp-btn:hover:not(:disabled) { opacity: 0.88; transform: translateY(-1px); }
        .lp-btn:disabled { opacity: 0.6; cursor: not-allowed; }

        .lp-btn-spinner {
          width: 15px; height: 15px;
          border: 2px solid rgba(255,255,255,0.3);
          border-top-color: #fff;
          border-radius: 50%;
          animation: spin 0.65s linear infinite;
          flex-shrink: 0;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .lp-card-footer {
          text-align: center;
          font-size: 13px;
          color: rgba(255,255,255,0.40);
        }
        .lp-card-footer a {
          color: rgba(255,255,255,0.78);
          font-weight: 600;
          text-decoration: none;
          cursor: pointer;
        }
        .lp-card-footer a:hover { color: #fff; text-decoration: underline; }

        @media (max-width: 820px) {
          .lp-layout { flex-direction: column; padding: 32px 6%; align-items: flex-start; }
          .lp-card { width: 100%; }
        }
      `}</style>

      <div className="lp-root">
        <div className="lp-bg" style={{ backgroundImage: `url(${hope})` }} />
        <div className="lp-overlay" />

        <div className="lp-layout">

          {/* ── LEFT ── */}
          <div className="lp-left">
            <h1 className="lp-headline">
              Welcome to<br />
              <span className="cta-gradient-text">Sentio Mind</span>
            </h1>
            <p className="lp-sub">
              Sentio Mind turns behavioural signals into precise, actionable
              intelligence — so every individual is seen, heard, and supported.
              Built for supervisors, counsellors, and teachers across your institution.
            </p>
            <div className="lp-socials">

              {/* Facebook — brand blue */}
              <a href="https://www.facebook.com" target="_blank" rel="noopener" className="lp-social" aria-label="Facebook">
                <svg viewBox="0 0 24 24" fill="#1877F2">
                  <path d="M22.676 0H1.324C.593 0 0 .593 0 1.324v21.352C0 23.408.593 24 1.324 24h11.494v-9.294H9.689v-3.621h3.129V8.41c0-3.099 1.894-4.785 4.659-4.785 1.325 0 2.464.097 2.796.141v3.24h-1.921c-1.5 0-1.792.721-1.792 1.771v2.311h3.584l-.465 3.63H16.56V24h6.115c.733 0 1.325-.592 1.325-1.324V1.324C24 .593 23.408 0 22.676 0"/>
                </svg>
              </a>

              {/* X / Twitter — white */}
              <a href="https://wa.me/9277777707" target="_blank" rel="noopener" className="lp-social" aria-label="WhatsApp">
              <svg viewBox="0 0 24 24" fill="#25D366">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
                <path d="M12 0C5.373 0 0 5.373 0 12c0 2.127.558 4.126 1.532 5.858L.054 23.447a.5.5 0 0 0 .617.601l5.796-1.522A11.94 11.94 0 0 0 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.9a9.878 9.878 0 0 1-5.031-1.378l-.36-.214-3.733.98.997-3.648-.235-.374A9.86 9.86 0 0 1 2.1 12C2.1 6.525 6.525 2.1 12 2.1S21.9 6.525 21.9 12 17.475 21.9 12 21.9z"/>
              </svg>
              </a>

              {/* Instagram — gradient via linearGradient */}
              <a href="https://www.instagram.com/sentiomind?igsh=NGd6NGZtdDcxMGpk&utm_source=qr" target="_blank" rel="noopener" className="lp-social" aria-label="Instagram">
                <svg viewBox="0 0 24 24">
                  <defs>
                    <linearGradient id="ig-grad" x1="0%" y1="100%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#f09433"/>
                      <stop offset="25%" stopColor="#e6683c"/>
                      <stop offset="50%" stopColor="#dc2743"/>
                      <stop offset="75%" stopColor="#cc2366"/>
                      <stop offset="100%" stopColor="#bc1888"/>
                    </linearGradient>
                  </defs>
                  <path fill="url(#ig-grad)" d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/>
                </svg>
              </a>

              {/* YouTube — brand red */}
              <a href="https://www.linkedin.com/company/sentio-mind" target="_blank" rel="noopener" className="lp-social" aria-label="LinkedIn">
               <svg viewBox="0 0 24 24" fill="#0A66C2">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
              </svg>
              </a>

            </div>
          </div>

          {/* ── RIGHT: card ── */}
          <div className="lp-card">
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "22px" }}>
              <img src={logo} alt="Sentio Mind" style={{ width: 46, height: 46, objectFit: "contain", borderRadius: 10 }} />
              <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "26px", fontWeight: 700, letterSpacing: "-0.3px" }}>
                <span style={{ color: "#7ffff4" }}>Sentio </span>
                <span style={{ color: "#a0f0e8" }}>Mind</span>
              </span>
            </div>

            <div className="lp-card-title">Log in to your account</div>
            <div className="lp-card-sub">Welcome — select a method to continue</div>

            <div className="lp-divider">sign in with email</div>

            {error && <div className="lp-error">{error}</div>}

            <form onSubmit={handleSignIn}>
              <div className="lp-field">
                <span className="lp-field-logo">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
                  </svg>
                </span>
                <input
                  className="lp-input"
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                />
              </div>

              <div className="lp-field">
                <span className="lp-field-logo">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                  </svg>
                </span>
                <input
                  className="lp-input"
                  type={showPass ? "text" : "password"}
                  placeholder="Password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="lp-eye-btn"
                  onClick={() => setShowPass(v => !v)}
                  tabIndex={-1}
                  aria-label={showPass ? "Hide password" : "Show password"}
                >
                  {showPass
                    ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                    : <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  }
                </button>
              </div>

              <div className="lp-meta">
                <label className="lp-remember">
                  <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />
                  Remember me
                </label>
                <a href="#" className="lp-forgot">Forgot Password?</a>
              </div>

              <button className="lp-btn" type="submit" disabled={loading}>
                {loading && <span className="lp-btn-spinner" />}
                {loading ? "Signing in…" : "Login"}
              </button>
            </form>

            <div className="lp-card-footer">
              Don't have an account?{" "}
              <a onClick={() => navigate("/signup")} style={{cursor:"pointer"}}>Create one</a>
            </div>
          </div>

        </div>
      </div>
    </>
  );
}