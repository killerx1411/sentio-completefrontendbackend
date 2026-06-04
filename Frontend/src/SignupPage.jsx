import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { signup } from "./services/authApi";
import hope from "./assets/hope.jpg";
import icon from "./assets/icon.png";
import logo from "./assets/logo.png";
function ThankYouStep({ onHome }) {
  return (
    <div style={{ textAlign: "center", padding: "8px 0 4px" }}>
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: "50%",
          background: "rgba(61,214,208,0.12)",
          border: "1.5px solid rgba(61,214,208,0.35)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          margin: "0 auto 20px",
        }}
      >
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#3dd6d0"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>
      <div style={{ fontSize: 20, fontWeight: 700, color: "#fff", marginBottom: 8 }}>
        Thank you
      </div>
      <div
        style={{
          fontSize: 14,
          color: "rgba(255,255,255,0.55)",
          lineHeight: 1.7,
          marginBottom: 28,
        }}
      >
        We will reach out to you shortly. Once your account is approved, you will receive an email
        with login details for your Sentio Mind dashboard.
      </div>
      <button className="lp-btn" type="button" onClick={onHome} style={{ marginBottom: 0 }}>
        Back to home
      </button>
    </div>
  );
}

export default function SignupPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState("register");
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    organization: "",
    message: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function setField(key) {
    return (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.name || !form.email) {
      setError("Please enter your name and email.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await signup({
        full_name: form.name,
        email: form.email,
        phone: form.phone || undefined,
        organization: form.organization || undefined,
        message: form.message || undefined,
      });
      setStep("thanks");
    } catch (err) {
      setError(err.message || "Registration failed. Please try again.");
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
        .cta-gradient-text {
          background: linear-gradient(90deg, #7ffff4, #a0f0e8);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .lp-root {
          position: relative; height: 100vh; width: 100vw;
          overflow: hidden; font-family: 'Inter', sans-serif;
          display: flex; align-items: center;
        }
        .lp-bg { position: absolute; inset: 0; background-size: cover; background-position: center; }
        .lp-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.42); }
        .lp-layout {
          position: relative; z-index: 2; width: 100%;
          display: flex; align-items: center; justify-content: space-between;
          padding: 0 6%; gap: 40px;
        }
        .lp-left { flex: 1; color: #fff; max-width: 520px; }
        .lp-headline {
          font-size: clamp(38px, 4.5vw, 60px); font-weight: 800;
          line-height: 1.12; color: #fff; margin-bottom: 22px;
          letter-spacing: -0.5px;
        }
        .lp-sub {
          font-size: clamp(14px, 1.3vw, 17px); line-height: 1.80;
          color: rgba(255,255,255,0.88); max-width: 420px;
        }
        .lp-card {
          width: 430px; flex-shrink: 0;
          background: rgba(28,30,38,0.82); backdrop-filter: blur(28px);
          border-radius: 20px; border: 1px solid rgba(255,255,255,0.12);
          padding: 40px 38px 34px; color: #fff;
        }
        .lp-card-title { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
        .lp-card-sub { font-size: 13px; color: rgba(255,255,255,0.45); margin-bottom: 24px; }
        .lp-field { position: relative; margin-bottom: 13px; }
        .lp-field-icon {
          position: absolute; left: 14px; top: 50%; transform: translateY(-50%);
          color: rgba(255,255,255,0.38); pointer-events: none;
        }
        .lp-input {
          width: 100%; padding: 13px 16px;
          background: rgba(255,255,255,0.09); border: 1px solid rgba(255,255,255,0.14);
          border-radius: 10px; color: #fff; font-size: 15px;
          font-family: 'Inter', sans-serif; outline: none;
        }
        .lp-input:focus { border-color: rgba(61,214,208,0.5); }
        .lp-textarea {
          width: 100%; min-height: 80px; padding: 12px;
          background: rgba(255,255,255,0.09); border: 1px solid rgba(255,255,255,0.14);
          border-radius: 10px; color: #fff; font-size: 14px;
          font-family: 'Inter', sans-serif; resize: vertical;
        }
        .lp-error {
          font-size: 13px; color: #ff9090;
          background: rgba(255,60,60,0.10); border: 1px solid rgba(255,60,60,0.22);
          border-radius: 9px; padding: 10px 14px; margin-bottom: 14px;
        }
        .lp-btn {
          width: 100%; padding: 14px;
          background: linear-gradient(135deg, #4a8a94 0%, #3dd6d0 100%);
          border: none; border-radius: 10px; color: #fff;
          font-size: 15px; font-weight: 600; font-family: 'Inter', sans-serif;
          cursor: pointer; margin-bottom: 16px;
        }
        .lp-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .lp-card-footer { text-align: center; font-size: 13px; color: rgba(255,255,255,0.40); }
        .lp-card-footer a { color: rgba(255,255,255,0.78); font-weight: 600; cursor: pointer; }
        @media (max-width: 820px) {
          .lp-layout { flex-direction: column; padding: 28px 5%; }
          .lp-card { width: 100%; }
        }
      `}</style>

      <div className="lp-root">
        <div className="lp-bg" style={{ backgroundImage: `url(${hope})` }} />
        <div className="lp-overlay" />

        <div className="lp-layout">
          <div className="lp-left">
            <h1 className="lp-headline">
              Request access to
              <br />
              <span className="cta-gradient-text">Sentio Mind</span>
            </h1>
            <p className="lp-sub">
              Tell us about yourself. Our team will review your request and email you login details
              once your role is confirmed.
            </p>
          </div>

          <div className="lp-card">
            <div style={{ display: "flex", alignItems: "center", gap: 11, marginBottom: 20 }}>
            <img src={logo} alt="Sentio Mind" style={{ width: 46, height: 46, objectFit: "contain", borderRadius: 10 }} />
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "26px", fontWeight: 700, letterSpacing: "-0.3px" }}>
                <span style={{ color: "#7ffff4" }}>Sentio </span>
                <span style={{ color: "#a0f0e8" }}>Mind</span>
              </span>
            </div>

            {step === "register" ? (
              <>
                <div className="lp-card-title">Create your request</div>
                <div className="lp-card-sub">No password needed — we will send credentials after approval</div>

                <form onSubmit={handleSubmit}>
                  <div className="lp-field">
                     
                    <input
                      className="lp-input"
                      placeholder="Full name"
                      value={form.name}
                      onChange={setField("name")}
                      required
                    />
                  </div>
                  <div className="lp-field">
                     
                    <input
                      className="lp-input"
                      type="email"
                      placeholder="Email"
                      value={form.email}
                      onChange={setField("email")}
                      required
                    />
                  </div>
                  <div className="lp-field">
                    
                    <input
                      className="lp-input"
                      placeholder="Phone (optional)"
                      value={form.phone}
                      onChange={setField("phone")}
                    />
                  </div>
                  <div className="lp-field">
                     
                    <input
                      className="lp-input"
                      placeholder="School / organization"
                      value={form.organization}
                      onChange={setField("organization")}
                    />
                  </div>
                  <div style={{ marginBottom: 14 }}>
                    <textarea
                      className="lp-textarea"
                      placeholder="Message (optional)"
                      value={form.message}
                      onChange={setField("message")}
                    />
                  </div>

                  {error && <div className="lp-error">{error}</div>}

                  <button className="lp-btn" type="submit" disabled={loading}>
                    {loading ? "Submitting…" : "Submit request"}
                  </button>
                </form>

                <div className="lp-card-footer">
                  Already have credentials? <a onClick={() => navigate("/")}>Sign in</a>
                </div>
              </>
            ) : (
              <ThankYouStep onHome={() => navigate("/")} />
            )}
          </div>
        </div>
      </div>
    </>
  );
}
