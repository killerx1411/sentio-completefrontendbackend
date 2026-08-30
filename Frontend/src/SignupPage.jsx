// SECURITY NOTE: This component uses an inline <style> tag which requires unsafe-inline in CSP style-src.
// Consider migrating to CSS modules or a CSS-in-JS solution with nonce support in a future refactor.

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { signup } from "./services/authApi";
import logo from "./assets/logo.png";

/* ─────────────────────────────────────────────
   VALIDATION HELPERS  (all original — untouched)
───────────────────────────────────────────── */
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_REGEX = /^[\d\s+\-()]+$/;

function containsNullByte(value) {
  return typeof value === "string" && value.includes("\u0000");
}

function validatePhone(phone) {
  if (!phone) return "";
  if (!PHONE_REGEX.test(phone) || phone.length < 7 || phone.length > 15) {
    return "Phone must be 7–15 characters and contain only digits, spaces, +, -, (, ).";
  }
  return "";
}

/* ─────────────────────────────────────────────
   STYLES  — v4 design tokens + signup-specific
───────────────────────────────────────────── */
const styles = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=Poppins:wght@500;600;700&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body, #root { height: 100%; }

  :root {
    --deep-teal:  #0F4C5C;
    --aqua-teal:  #2EC4B6;
    --soft-blue:  #6FBEDC;
    --off-white:  #F7F9FB;
    --charcoal:   #3A3F45;
    --border:     rgba(15, 76, 92, 0.13);
    --muted:      #8A9299;
    --text:       #1A2328;
    --text-sec:   #5A6470;
  }

  /* ── Layout ── */
  .sm-layout {
    display: flex;
    width: 100%; min-height: 100vh;
  }

  /* ── LEFT PANEL ── */
  .sm-left {
    width: 52%;
    background: var(--deep-teal);
    display: flex; flex-direction: column;
    justify-content: space-between;
    padding: 52px 64px;
    position: relative; overflow: hidden;
  }

  .sm-left-overlay {
    position: absolute; inset: 0;
    background: rgba(10, 50, 60, 0.72);
  }

  .sm-left::before {
    content: '';
    position: absolute; inset: 0;
    background-image:
      repeating-linear-gradient(0deg, transparent, transparent 59px, rgba(46,196,182,0.06) 59px, rgba(46,196,182,0.06) 60px),
      repeating-linear-gradient(90deg, transparent, transparent 59px, rgba(46,196,182,0.06) 59px, rgba(46,196,182,0.06) 60px);
    pointer-events: none;
    z-index: 1;
  }

  .sm-circle {
    position: absolute; border-radius: 50%;
    border: 1px solid rgba(46,196,182,0.16);
    pointer-events: none; z-index: 1;
  }
  .sm-circle-1 { width: 460px; height: 460px; bottom: -130px; right: -150px; }
  .sm-circle-2 { width: 250px; height: 250px; bottom: -50px; right: -50px; border-color: rgba(111,190,220,0.12); }
  .sm-circle-3 { width: 170px; height: 170px; top: 110px; right: -65px; border-color: rgba(46,196,182,0.09); }

  /* Brand */
  .sm-brand {
    display: flex; align-items: center; gap: 12px;
    position: relative; z-index: 2;
  }
  .sm-brand-name {
    font-family: 'Poppins', sans-serif;
    font-size: 20px; font-weight: 600;
    color: #fff; letter-spacing: -0.2px;
  }
  .sm-brand-name span { color: var(--aqua-teal); }

  /* Panel body */
  .sm-panel-body {
    position: relative; z-index: 2;
    flex: 1; display: flex; flex-direction: column;
    justify-content: center; padding: 48px 0;
  }
  .sm-eyebrow {
    font-size: 11px; font-weight: 500;
    letter-spacing: 2.5px; text-transform: uppercase;
    color: var(--aqua-teal); margin-bottom: 20px;
    display: flex; align-items: center; gap: 10px;
  }
  .sm-eyebrow::before {
    content: ''; display: block;
    width: 24px; height: 1px;
    background: var(--aqua-teal); opacity: 0.7;
  }
  .sm-headline {
    font-family: 'Poppins', sans-serif;
    font-size: clamp(30px, 3.2vw, 46px);
    font-weight: 700; color: #fff;
    line-height: 1.18; letter-spacing: -0.5px;
    max-width: 400px; margin-bottom: 26px;
    text-shadow: 0 2px 16px rgba(0,0,0,0.45);
  }
  .sm-headline em { font-style: normal; color: var(--aqua-teal); }
  .sm-panel-sub {
    font-size: 15px; line-height: 1.75;
    color: rgba(255,255,255,0.72);
    max-width: 370px; margin-bottom: 40px;
    text-shadow: 0 1px 8px rgba(0,0,0,0.5);
  }

  /* Steps indicator on left panel */
  .sm-steps {
    display: flex; flex-direction: column; gap: 14px;
    position: relative; z-index: 2;
  }
  .sm-step {
    display: flex; align-items: flex-start; gap: 14px;
  }
  .sm-step-num {
    width: 26px; height: 26px; flex-shrink: 0;
    border-radius: 50%;
    border: 1px solid rgba(46,196,182,0.35);
    display: flex; align-items: center; justify-content: center;
    font-family: 'Poppins', sans-serif;
    font-size: 11px; font-weight: 600;
    color: var(--aqua-teal);
    margin-top: 1px;
  }
  .sm-step-text {
    font-family: 'DM Sans', sans-serif;
    font-size: 13.5px; line-height: 1.55;
    color: rgba(255,255,255,0.65);
  }
  .sm-step-text strong {
    display: block;
    color: rgba(255,255,255,0.90);
    font-weight: 500; margin-bottom: 2px;
  }

  /* Trust badges */
  .sm-panel-footer { position: relative; z-index: 2; display: flex; gap: 10px; flex-wrap: wrap; }
  .sm-badge {
    display: flex; align-items: center; gap: 7px;
    padding: 7px 13px; border-radius: 100px;
    border: 1px solid rgba(46,196,182,0.20);
    font-size: 11px; font-weight: 500;
    color: rgba(255,255,255,0.50); letter-spacing: 0.3px;
    font-family: 'DM Sans', sans-serif;
  }
  .sm-badge-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--aqua-teal); flex-shrink: 0;
  }

  /* ── RIGHT PANEL ── */
  .sm-right {
    flex: 1; display: flex;
    align-items: center; justify-content: center;
    padding: 48px 56px;
    background: var(--off-white);
    overflow-y: auto;
  }
  .sm-card { width: 100%; max-width: 440px; }

  .sm-card-header { margin-bottom: 28px; }
  .sm-card-title {
    font-family: 'Poppins', sans-serif;
    font-size: 26px; font-weight: 700;
    color: var(--deep-teal); letter-spacing: -0.4px;
    line-height: 1.2; margin-bottom: 8px;
  }
  .sm-card-sub {
    font-size: 14px; color: var(--text-sec); line-height: 1.6;
    font-family: 'DM Sans', sans-serif;
  }

  /* Divider */
  .sm-divider {
    display: flex; align-items: center;
    gap: 14px; margin-bottom: 22px;
  }
  .sm-divider-line { flex: 1; height: 1px; background: var(--border); }
  .sm-divider-label {
    font-size: 11.5px; color: var(--muted);
    letter-spacing: 0.5px; white-space: nowrap;
    font-family: 'DM Sans', sans-serif;
  }

  /* Fields */
  .sm-field { margin-bottom: 13px; }
  .sm-label {
    display: block; font-size: 12.5px; font-weight: 500;
    color: var(--charcoal); margin-bottom: 7px;
    letter-spacing: 0.2px; font-family: 'DM Sans', sans-serif;
  }
  .sm-field-wrap { position: relative; }
  .sm-field-icon {
    position: absolute; left: 14px; top: 50%;
    transform: translateY(-50%);
    color: var(--muted); display: flex; align-items: center;
    pointer-events: none;
  }
  .sm-input {
    width: 100%; padding: 12px 14px 12px 42px;
    border-radius: 8px; border: 1px solid var(--border);
    background: #fff; font-family: 'DM Sans', sans-serif;
    font-size: 14px; color: var(--text); outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
    -webkit-appearance: none;
  }
  .sm-input-bare {
    width: 100%; padding: 12px 14px;
    border-radius: 8px; border: 1px solid var(--border);
    background: #fff; font-family: 'DM Sans', sans-serif;
    font-size: 14px; color: var(--text); outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
    -webkit-appearance: none;
  }
  .sm-textarea {
    width: 100%; padding: 12px 14px;
    border-radius: 8px; border: 1px solid var(--border);
    background: #fff; font-family: 'DM Sans', sans-serif;
    font-size: 14px; color: var(--text); outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
    -webkit-appearance: none;
    resize: vertical; min-height: 80px;
    line-height: 1.6;
  }
  .sm-input::placeholder,
  .sm-input-bare::placeholder,
  .sm-textarea::placeholder { color: #B8C0C8; }
  .sm-input:hover,
  .sm-input-bare:hover,
  .sm-textarea:hover { border-color: rgba(46,196,182,0.40); }
  .sm-input:focus,
  .sm-input-bare:focus,
  .sm-textarea:focus {
    border-color: var(--aqua-teal);
    box-shadow: 0 0 0 3px rgba(46,196,182,0.12);
  }

  /* Optional badge on label */
  .sm-optional {
    font-size: 11px; color: var(--muted);
    font-weight: 400; margin-left: 5px;
    letter-spacing: 0px;
  }

  /* Error */
  .sm-error {
    font-size: 13px; color: #b91c1c;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 8px; padding: 10px 14px;
    margin-bottom: 14px; line-height: 1.5;
    font-family: 'DM Sans', sans-serif;
  }
  /* Field-level error (tight, no background box) */
  .sm-field-error {
    font-size: 12px; color: #b91c1c;
    margin-top: 5px; line-height: 1.4;
    font-family: 'DM Sans', sans-serif;
    display: flex; align-items: flex-start; gap: 5px;
  }

  /* Submit */
  .sm-submit {
    width: 100%; padding: 13px; border-radius: 8px;
    border: none; background: var(--deep-teal);
    color: #fff; font-family: 'DM Sans', sans-serif;
    font-size: 14.5px; font-weight: 600; cursor: pointer;
    transition: background 0.2s, transform 0.12s;
    display: flex; align-items: center;
    justify-content: center; gap: 8px;
    letter-spacing: 0.1px; margin-bottom: 18px;
  }
  .sm-submit:hover:not(:disabled) {
    background: #0a3647; transform: translateY(-1px);
  }
  .sm-submit:active:not(:disabled) {
    transform: translateY(0) scale(0.99);
  }
  .sm-submit:disabled { opacity: 0.65; cursor: not-allowed; }

  .sm-spinner {
    width: 15px; height: 15px;
    border: 2px solid rgba(255,255,255,0.25);
    border-top-color: #fff; border-radius: 50%;
    animation: smSpin 0.65s linear infinite; flex-shrink: 0;
  }
  @keyframes smSpin { to { transform: rotate(360deg); } }

  /* Footer */
  .sm-card-footer {
    text-align: center; font-size: 13px;
    color: var(--muted);
    padding-top: 16px; border-top: 1px solid var(--border);
    font-family: 'DM Sans', sans-serif;
  }
  .sm-card-footer a {
    color: var(--deep-teal); font-weight: 600;
    text-decoration: none; transition: color 0.15s;
    cursor: pointer;
  }
  .sm-card-footer a:hover { color: var(--aqua-teal); }

  .sm-brand-logo {
    width: 46px; height: 46px; object-fit: contain; border-radius: 10px;
  }
  .sm-field-error-icon { flex-shrink: 0; margin-top: 1px; }

  .sm-terms { margin-bottom: 14px; }
  .sm-terms-label {
    display: flex; align-items: flex-start; gap: 10px;
    font-size: 13px; line-height: 1.55; color: var(--text-sec);
    font-family: 'DM Sans', sans-serif; cursor: pointer;
  }
  .sm-terms-label input { margin-top: 3px; flex-shrink: 0; }
  .sm-terms-link {
    color: var(--aqua-teal); text-decoration: underline;
  }
  .sm-terms-link:hover { color: var(--deep-teal); }
  .sm-terms-error {
    font-size: 12px; color: #b91c1c; margin-top: 6px;
    font-family: 'DM Sans', sans-serif;
  }

  /* Thank-you success state */
  .sm-success-icon {
    width: 56px; height: 56px; border-radius: 50%;
    background: rgba(46,196,182,0.10);
    border: 1px solid rgba(46,196,182,0.25);
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 22px;
  }
  .sm-success-title {
    font-family: 'Poppins', sans-serif;
    font-size: 22px; font-weight: 700;
    color: var(--deep-teal); letter-spacing: -0.3px;
    margin-bottom: 10px;
  }
  .sm-success-body {
    font-size: 14px; color: var(--text-sec);
    line-height: 1.7; margin-bottom: 28px;
    font-family: 'DM Sans', sans-serif;
  }

  /* ── RESPONSIVE ── */
  @media (max-width: 900px) {
    .sm-left { display: none; }
    .sm-right { padding: 48px 28px; }
  }
  @media (max-width: 480px) {
    .sm-right { padding: 36px 20px; }
  }
`;

/* ─────────────────────────────────────────────
   SVG ICONS
───────────────────────────────────────────── */
function IconEmail() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
      <polyline points="22,6 12,13 2,6"/>
    </svg>
  );
}

function IconUser() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>
  );
}

function IconPhone() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 1.18h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.76a16 16 0 0 0 6.16 6.16l.95-.95a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>
    </svg>
  );
}

function IconBuilding() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
      <polyline points="9 22 9 12 15 12 15 22"/>
    </svg>
  );
}

/* ─────────────────────────────────────────────
   THANK YOU STEP
───────────────────────────────────────────── */
function ThankYouStep({ onHome }) {
  return (
    <>
      <div className="sm-success-icon">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#2EC4B6" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>
      <div className="sm-success-title">Request submitted</div>
      <p className="sm-success-body">
        We will reach out to you shortly. Once your account is approved, you will receive an email with login details for your Sentio Mind dashboard.
      </p>
      <button className="sm-submit" type="button" onClick={onHome}>
        Back to login
      </button>
    </>
  );
}

/* ─────────────────────────────────────────────
   MAIN COMPONENT
───────────────────────────────────────────── */
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
  const [phoneError, setPhoneError] = useState("");
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [termsError, setTermsError] = useState("");
  const [loading, setLoading] = useState(false);

  function setField(key) {
    return (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (loading) return;

    const sanitized = {
      name: form.name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim(),
      organization: form.organization.trim(),
      message: form.message.trim(),
    };

    const fields = Object.values(sanitized);
    if (fields.some(containsNullByte)) {
      setError("Invalid characters in input.");
      return;
    }

    if (!sanitized.name || !sanitized.email) {
      setError("Please enter your name and email.");
      return;
    }

    if (!EMAIL_REGEX.test(sanitized.email)) {
      setError("Please enter a valid email address.");
      return;
    }

    const phoneValidationError = validatePhone(sanitized.phone);
    if (phoneValidationError) {
      setPhoneError(phoneValidationError);
      return;
    }
    setPhoneError("");

    if (!termsAccepted) {
      setTermsError("You must accept the Terms & Conditions to create an account.");
      return;
    }
    setTermsError("");

    setError("");
    setLoading(true);
    try {
      await signup({
        full_name: sanitized.name,
        email: sanitized.email,
        phone: sanitized.phone || undefined,
        organization: sanitized.organization || undefined,
        message: sanitized.message || undefined,
        terms_accepted: true,
      });
      setStep("thanks");
    } catch {
      setError("Submission failed. Please check your details and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <style>{styles}</style>

      <div className="sm-layout">

        {/* ── LEFT PANEL ─────────────────────────────── */}
        <div className="sm-left">
          <div className="sm-left-overlay" />
          <div className="sm-circle sm-circle-1" />
          <div className="sm-circle sm-circle-2" />
          <div className="sm-circle sm-circle-3" />

          {/* Brand */}
          <div className="sm-brand">
            <img
              src={logo}
              alt="Sentio Mind"
              className="sm-brand-logo"
            />
            <div className="sm-brand-name">
              Sentio <span>Mind</span>
            </div>
          </div>

          {/* Body */}
          <div className="sm-panel-body">
            <div className="sm-eyebrow">Request Access</div>
            <h1 className="sm-headline">
              Join your<br />
              institution's<br />
              <em>intelligence layer.</em>
            </h1>
            <p className="sm-panel-sub">
              Tell us about yourself. Our team reviews every request and sends verified credentials once your role is confirmed.
            </p>

            {/* How it works steps */}
            <div className="sm-steps">
              {[
                { label: "Submit your request", desc: "Fill in your details — no password needed at this stage." },
                { label: "Team review", desc: "We verify your role and institution within 1–2 working days." },
                { label: "Receive credentials", desc: "Login details arrive in your inbox. Sign in and get started." },
              ].map((s, i) => (
                <div className="sm-step" key={i}>
                  <div className="sm-step-num">{i + 1}</div>
                  <div className="sm-step-text">
                    <strong>{s.label}</strong>
                    {s.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Trust badges */}
          <div className="sm-panel-footer">
            {["DPDP Act 2023 Compliant", "Encrypted Biometric Storage", "Opt-Out Guaranteed"].map(label => (
              <div className="sm-badge" key={label}>
                <div className="sm-badge-dot" />
                {label}
              </div>
            ))}
          </div>
        </div>

        {/* ── RIGHT PANEL ────────────────────────────── */}
        <div className="sm-right">
          <div className="sm-card">

            {step === "thanks" ? (
              <ThankYouStep onHome={() => navigate("/")} />
            ) : (
              <>
                <div className="sm-card-header">
                  <h2 className="sm-card-title">Request access</h2>
                  <p className="sm-card-sub">
                    No password needed — we will send credentials after approval.
                  </p>
                </div>

                <div className="sm-divider">
                  <div className="sm-divider-line" />
                  <div className="sm-divider-label">your details</div>
                  <div className="sm-divider-line" />
                </div>

                {error && <div className="sm-error" role="alert">{error}</div>}

                <form onSubmit={handleSubmit} noValidate>

                  {/* Full name */}
                  <div className="sm-field">
                    <label className="sm-label" htmlFor="su-name">Full name</label>
                    <div className="sm-field-wrap">
                      <span className="sm-field-icon"><IconUser /></span>
                      <input
                        id="su-name"
                        className="sm-input"
                        type="text"
                        placeholder="Your full name"
                        value={form.name}
                        onChange={setField("name")}
                        maxLength={100}
                        required
                        aria-required="true"
                        autoComplete="name"
                      />
                    </div>
                  </div>

                  {/* Email */}
                  <div className="sm-field">
                    <label className="sm-label" htmlFor="su-email">Email address</label>
                    <div className="sm-field-wrap">
                      <span className="sm-field-icon"><IconEmail /></span>
                      <input
                        id="su-email"
                        className="sm-input"
                        type="email"
                        placeholder="you@institution.edu"
                        value={form.email}
                        onChange={setField("email")}
                        maxLength={100}
                        required
                        aria-required="true"
                        autoComplete="email"
                      />
                    </div>
                  </div>

                  {/* Phone */}
                  <div className="sm-field">
                    <label className="sm-label" htmlFor="su-phone">
                      Phone
                      <span className="sm-optional">optional</span>
                    </label>
                    <div className="sm-field-wrap">
                      <span className="sm-field-icon"><IconPhone /></span>
                      <input
                        id="su-phone"
                        className="sm-input"
                        type="tel"
                        placeholder="+91 98765 43210"
                        value={form.phone}
                        onChange={(e) => {
                          setField("phone")(e);
                          if (phoneError) setPhoneError("");
                        }}
                        maxLength={20}
                        autoComplete="tel"
                      />
                    </div>
                    {phoneError && (
                      <div className="sm-field-error" role="alert">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="sm-field-error-icon">
                          <circle cx="12" cy="12" r="10"/>
                          <line x1="12" y1="8" x2="12" y2="12"/>
                          <line x1="12" y1="16" x2="12.01" y2="16"/>
                        </svg>
                        {phoneError}
                      </div>
                    )}
                  </div>

                  {/* Organization */}
                  <div className="sm-field">
                    <label className="sm-label" htmlFor="su-org">
                      School or organization
                      <span className="sm-optional">optional</span>
                    </label>
                    <div className="sm-field-wrap">
                      <span className="sm-field-icon"><IconBuilding /></span>
                      <input
                        id="su-org"
                        className="sm-input"
                        type="text"
                        placeholder="Institution name"
                        value={form.organization}
                        onChange={setField("organization")}
                        maxLength={100}
                        autoComplete="organization"
                      />
                    </div>
                  </div>

                  {/* Message */}
                  <div className="sm-field">
                    <label className="sm-label" htmlFor="su-message">
                      Message
                      <span className="sm-optional">optional</span>
                    </label>
                    <textarea
                      id="su-message"
                      className="sm-textarea"
                      placeholder="Tell us about your role or how you plan to use Sentio Mind…"
                      value={form.message}
                      onChange={setField("message")}
                      maxLength={500}
                    />
                  </div>

                  <div className="sm-terms">
                    <label className="sm-terms-label" htmlFor="terms-checkbox">
                      <input
                        id="terms-checkbox"
                        name="terms_accepted"
                        type="checkbox"
                        checked={termsAccepted}
                        onChange={(e) => {
                          setTermsAccepted(e.target.checked);
                          if (termsError) setTermsError("");
                        }}
                      />
                      <span>
                        I agree to the{" "}
                        <a
                          href="#"
                          className="sm-terms-link"
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Terms &amp; Conditions
                        </a>{" "}
                        and{" "}
                        <a
                          href="#"
                          className="sm-terms-link"
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Privacy Policy
                        </a>
                      </span>
                    </label>
                    {termsError && (
                      <div className="sm-terms-error" role="alert">
                        {termsError}
                      </div>
                    )}
                  </div>

                  <button
                    className="sm-submit"
                    type="submit"
                    disabled={loading}
                  >
                    {loading && <span className="sm-spinner" />}
                    {loading ? "Submitting…" : "Submit request"}
                  </button>

                </form>

                <div className="sm-card-footer">
                  Already have credentials?{" "}
                  <a onClick={() => navigate("/")}>Sign in</a>
                </div>
              </>
            )}

          </div>
        </div>

      </div>
    </>
  );
}