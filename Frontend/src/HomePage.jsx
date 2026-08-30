// VERSION 4 UI + VERSION 1 FEATURES (merged)

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useSession } from "./context/SessionContext";
import { getDashboardPathForUser } from "./utils/roleRoutes";
import { requestPasswordReset } from "./services/authApi";
import logo from "./assets/logo.png";

/* ─────────────────────────────────────────────
   CLIENT-SIDE LOGIN RATE LIMITING (in-memory only — not localStorage/sessionStorage)
───────────────────────────────────────────── */
let loginFailedAttempts = 0;
let loginLockoutUntil = 0;
const LOGIN_MAX_ATTEMPTS = 5;
const LOGIN_LOCKOUT_SECONDS = 900;

/* ─────────────────────────────────────────────
   STYLES (Version 4 UI — unchanged)
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

  /* ── Loading screen ── */
  .sm-loading {
    height: 100vh;
    display: flex; align-items: center; justify-content: center;
    background: var(--off-white);
    font-family: 'DM Sans', sans-serif;
    font-size: 14px; color: var(--muted);
    gap: 10px;
  }
  .sm-loading-spinner {
    width: 18px; height: 18px;
    border: 2px solid rgba(15,76,92,0.15);
    border-top-color: var(--aqua-teal);
    border-radius: 50%;
    animation: smSpin 0.7s linear infinite;
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

  /* Background image */
  .sm-left-bg {
    position: absolute; inset: 0;
    background-size: cover;
    background-position: center;
  }

  /* Dark overlay over the image */
  .sm-left-overlay {
    position: absolute; inset: 0;
    background: rgba(10, 50, 60, 0.72);
  }

  /* Subtle grid texture on top of overlay */
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

  /* Social links */
  .sm-socials {
    display: flex; gap: 10px; align-items: center;
  }
  .sm-social {
    width: 38px; height: 38px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 10px;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.18);
    text-decoration: none;
    transition: background 0.18s, transform 0.18s;
    flex-shrink: 0;
  }
  .sm-social:hover {
    background: rgba(255,255,255,0.24);
    transform: translateY(-2px);
  }
  .sm-social svg { width: 18px; height: 18px; }

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
  }
  .sm-card { width: 100%; max-width: 420px; }

  .sm-card-header { margin-bottom: 32px; }
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
  .sm-field { margin-bottom: 15px; }
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
  .sm-input::placeholder,
  .sm-input-bare::placeholder { color: #B8C0C8; }
  .sm-input:hover,
  .sm-input-bare:hover { border-color: rgba(46,196,182,0.40); }
  .sm-input:focus,
  .sm-input-bare:focus {
    border-color: var(--aqua-teal);
    box-shadow: 0 0 0 3px rgba(46,196,182,0.12);
  }
  /* MFA code input — centered large digits */
  .sm-input-otp {
    width: 100%; padding: 14px;
    border-radius: 8px; border: 1px solid var(--border);
    background: #fff; font-family: 'DM Sans', sans-serif;
    font-size: 22px; font-weight: 600; letter-spacing: 10px;
    color: var(--text); outline: none; text-align: center;
    transition: border-color 0.2s, box-shadow 0.2s;
    -webkit-appearance: none;
  }
  .sm-input-otp::placeholder { color: #B8C0C8; letter-spacing: 8px; font-size: 18px; }
  .sm-input-otp:focus {
    border-color: var(--aqua-teal);
    box-shadow: 0 0 0 3px rgba(46,196,182,0.12);
  }

  .sm-eye-btn {
    position: absolute; right: 12px; top: 50%;
    transform: translateY(-50%);
    background: none; border: none; padding: 4px;
    cursor: pointer; color: var(--muted);
    display: flex; align-items: center;
    transition: color 0.15s; border-radius: 4px;
  }
  .sm-eye-btn:hover { color: var(--charcoal); }

  /* Meta row */
  .sm-meta {
    display: flex; align-items: center;
    justify-content: space-between;
    margin-bottom: 20px; margin-top: 2px;
  }
  .sm-remember {
    display: flex; align-items: center; gap: 8px;
    font-size: 13px; color: var(--text-sec);
    cursor: pointer; user-select: none;
    font-family: 'DM Sans', sans-serif;
  }
  .sm-remember input[type="checkbox"] {
    width: 15px; height: 15px;
    accent-color: var(--aqua-teal); cursor: pointer;
  }
  .sm-forgot-btn {
    font-size: 13px; font-weight: 500;
    color: var(--deep-teal); background: none; border: none;
    cursor: pointer; padding: 0;
    transition: color 0.15s; font-family: 'DM Sans', sans-serif;
  }
  .sm-forgot-btn:hover { color: var(--aqua-teal); }

  /* Error */
  .sm-error {
    font-size: 13px; color: #b91c1c;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 8px; padding: 10px 14px;
    margin-bottom: 16px; line-height: 1.5;
    font-family: 'DM Sans', sans-serif;
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

  /* Back link */
  .sm-back-btn {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 13px; font-weight: 500;
    color: var(--muted); background: none; border: none;
    cursor: pointer; padding: 0; margin-bottom: 24px;
    transition: color 0.15s; font-family: 'DM Sans', sans-serif;
  }
  .sm-back-btn:hover { color: var(--deep-teal); }

  /* Forgot-sent success state */
  .sm-success-icon {
    width: 52px; height: 52px; border-radius: 50%;
    background: rgba(46,196,182,0.12);
    border: 1px solid rgba(46,196,182,0.25);
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 20px;
  }

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
   LOADING SCREEN
───────────────────────────────────────────── */
function LoadingScreen() {
  return (
    <>
      <style>{styles}</style>
      <div className="sm-loading">
        <span className="sm-loading-spinner" />
        Authenticating…
      </div>
    </>
  );
}

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

function IconLock() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  );
}

function IconShield() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  );
}

function IconEyeOpen() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  );
}

function IconEyeClosed() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  );
}

/* ─────────────────────────────────────────────
   SOCIAL ICONS
───────────────────────────────────────────── */
function SocialLinks() {
  return (
    <div className="sm-socials">
      {/* Facebook */}
      <a href="https://www.facebook.com" target="_blank" rel="noopener noreferrer" className="sm-social" aria-label="Facebook">
        <svg viewBox="0 0 24 24" fill="#1877F2">
          <path d="M22.676 0H1.324C.593 0 0 .593 0 1.324v21.352C0 23.408.593 24 1.324 24h11.494v-9.294H9.689v-3.621h3.129V8.41c0-3.099 1.894-4.785 4.659-4.785 1.325 0 2.464.097 2.796.141v3.24h-1.921c-1.5 0-1.792.721-1.792 1.771v2.311h3.584l-.465 3.63H16.56V24h6.115c.733 0 1.325-.592 1.325-1.324V1.324C24 .593 23.408 0 22.676 0"/>
        </svg>
      </a>

      {/* WhatsApp */}
      <a href="https://wa.me/9277777707" target="_blank" rel="noopener noreferrer" className="sm-social" aria-label="WhatsApp">
        <svg viewBox="0 0 24 24" fill="#25D366">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
          <path d="M12 0C5.373 0 0 5.373 0 12c0 2.127.558 4.126 1.532 5.858L.054 23.447a.5.5 0 0 0 .617.601l5.796-1.522A11.94 11.94 0 0 0 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.9a9.878 9.878 0 0 1-5.031-1.378l-.36-.214-3.733.98.997-3.648-.235-.374A9.86 9.86 0 0 1 2.1 12C2.1 6.525 6.525 2.1 12 2.1S21.9 6.525 21.9 12 17.475 21.9 12 21.9z"/>
        </svg>
      </a>

      {/* Instagram */}
      <a href="https://www.instagram.com/sentiomind?igsh=NGd6NGZtdDcxMGpk&utm_source=qr" target="_blank" rel="noopener noreferrer" className="sm-social" aria-label="Instagram">
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

      {/* LinkedIn */}
      <a href="https://www.linkedin.com/company/sentio-mind" target="_blank" rel="noopener noreferrer" className="sm-social" aria-label="LinkedIn">
        <svg viewBox="0 0 24 24" fill="#0A66C2">
          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
        </svg>
      </a>
    </div>
  );
}

/* ─────────────────────────────────────────────
   MAIN COMPONENT
───────────────────────────────────────────── */
export default function HomePage() {

  const { isAuthenticated, initializing, loginWithCredentials, completeMfaLogin, user } = useSession();
  const navigate = useNavigate();

  // ── Login state ──
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [lockoutSecondsLeft, setLockoutSecondsLeft] = useState(0);

  // ── View router ──
  const [view, setView] = useState("login"); // "login" | "mfa" | "forgot" | "forgot-sent"

  // ── MFA state ──
  const [pendingToken, setPendingToken] = useState(null);
  const [totpCode,     setTotpCode]     = useState("");
  const [mfaError,     setMfaError]     = useState("");

  // ── Forgot password state ──
  const [forgotEmail,   setForgotEmail]   = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError,   setForgotError]   = useState("");
  const [forgotAttempts, setForgotAttempts] = useState(0);

  const isLoginLockedOut = lockoutSecondsLeft > 0;

  // ── Lockout countdown ticker ──
  useEffect(() => {
    function tickLockout() {
      const remaining = Math.max(0, Math.ceil((loginLockoutUntil - Date.now()) / 1000));
      setLockoutSecondsLeft(remaining);
      if (remaining === 0 && loginFailedAttempts >= LOGIN_MAX_ATTEMPTS) {
        loginFailedAttempts = 0;
      }
    }
    tickLockout();
    const id = setInterval(tickLockout, 1000);
    return () => clearInterval(id);
  }, []);

  // ── Auto-redirect when already authenticated ──
  useEffect(() => {
    if (!initializing && isAuthenticated && user) {
      navigate(getDashboardPathForUser(user), { replace: true });
    }
  }, [initializing, isAuthenticated, user, navigate]);

  if (initializing) return <LoadingScreen />;
  if (isAuthenticated) return <LoadingScreen />;

  /* ── HANDLERS ─────────────────────────────────────────── */

  async function handleSignIn(e) {
    e.preventDefault();
    if (isLoginLockedOut) return;
    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }
    setError("");
    setLoading(true);
    // SECURITY: never log password
    const normalizedEmail = email.trim().toLowerCase();
    try {
      const result = await loginWithCredentials(normalizedEmail, password, remember);
      if (result.mfaRequired) {
        setPendingToken(result.pendingToken);
        setTotpCode("");
        setMfaError("");
        setView("mfa");
        return;
      }
      loginFailedAttempts = 0;
      loginLockoutUntil = 0;
      setLockoutSecondsLeft(0);
      navigate(result.dashboardPath, { replace: true });
    } catch (err) {
      const rawMsg = err?.message || "";
      if (/locked/i.test(rawMsg) || /too many/i.test(rawMsg)) {
        setError("Account temporarily locked. Please try again later.");
      } else {
        loginFailedAttempts += 1;
        if (loginFailedAttempts >= LOGIN_MAX_ATTEMPTS) {
          loginLockoutUntil = Date.now() + LOGIN_LOCKOUT_SECONDS * 1000;
          setLockoutSecondsLeft(LOGIN_LOCKOUT_SECONDS);
        }
        setError("Invalid email or password.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleMfaVerify(e) {
    e.preventDefault();
    if (!pendingToken || !totpCode.trim()) {
      setMfaError("Enter your 6-digit authentication code.");
      return;
    }
    setMfaError("");
    setLoading(true);
    try {
      const { dashboardPath } = await completeMfaLogin(pendingToken, totpCode.trim());
      setPendingToken(null);
      setTotpCode("");
      loginFailedAttempts = 0;
      loginLockoutUntil = 0;
      setLockoutSecondsLeft(0);
      navigate(dashboardPath, { replace: true });
    } catch (err) {
      const rawMsg = err?.message || "";
      if (/rate/i.test(rawMsg) || err?.status === 429) {
        setMfaError("Too many attempts. Please wait and try again.");
      } else {
        setMfaError("Invalid code. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleForgotSubmit(e) {
    e.preventDefault();
    const sanitized = forgotEmail.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(sanitized)) {
      setForgotError("Please enter a valid email address.");
      return;
    }
    if (forgotAttempts >= 3) {
      setForgotError("Too many requests. Please wait before trying again.");
      return;
    }
    setForgotError("");
    setForgotLoading(true);
    setForgotAttempts(prev => prev + 1);
    try {
      await requestPasswordReset(sanitized);
    } catch {
      // SECURITY: swallow ALL errors — never reveal if email exists or not
    } finally {
      setForgotLoading(false);
      setView("forgot-sent");
    }
  }

  /* ── RENDER ─────────────────────────────────────────────── */
  return (
    <>
      <style>{styles}</style>

      <div className="sm-layout">

        {/* ── LEFT PANEL ─────────────────────────────── */}
        <div className="sm-left">
          <div className="sm-left-bg" />
          <div className="sm-left-overlay" />
          <div className="sm-circle sm-circle-1" />
          <div className="sm-circle sm-circle-2" />
          <div className="sm-circle sm-circle-3" />

          {/* Brand */}
          <div className="sm-brand">
            <img
              src={logo}
              alt="Sentio Mind"
              style={{ width: 46, height: 46, objectFit: "contain", borderRadius: 10 }}
            />
            <div className="sm-brand-name">
              Sentio <span>Mind</span>
            </div>
          </div>

          {/* Body */}
          <div className="sm-panel-body">
            <div className="sm-eyebrow">Behaviour Intelligence</div>
            <h1 className="sm-headline">
              Every signal.<br />
              Every individual.<br />
              <em>Understood.</em>
            </h1>
            <p className="sm-panel-sub">
              Sentio Mind turns real-time behavioural signals into precise, actionable intelligence — built for supervisors, counsellors, and teachers across your institution.
            </p>
            <SocialLinks />
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

            {/* ════════════════════════════
                VIEW: LOGIN
            ════════════════════════════ */}
            {view === "login" && (
              <>
                <div className="sm-card-header">
                  <h2 className="sm-card-title">Welcome back</h2>
                  <p className="sm-card-sub">Sign in to your Sentio Mind account to continue.</p>
                </div>

                <div className="sm-divider">
                  <div className="sm-divider-line" />
                  <div className="sm-divider-label">sign in with email</div>
                  <div className="sm-divider-line" />
                </div>

                {error && <div className="sm-error" role="alert">{error}</div>}

                <form onSubmit={handleSignIn} noValidate>

                  {/* Email */}
                  <div className="sm-field">
                    <label className="sm-label" htmlFor="sm-email">Email address</label>
                    <div className="sm-field-wrap">
                      <span className="sm-field-icon"><IconEmail /></span>
                      <input
                        id="sm-email"
                        className="sm-input"
                        type="email"
                        placeholder="you@institution.edu"
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                        autoComplete="email"
                        required
                        aria-required="true"
                      />
                    </div>
                  </div>

                  {/* Password */}
                  <div className="sm-field">
                    <label className="sm-label" htmlFor="sm-password">Password</label>
                    <div className="sm-field-wrap">
                      <span className="sm-field-icon"><IconLock /></span>
                      <input
                        id="sm-password"
                        className="sm-input"
                        type={showPass ? "text" : "password"}
                        placeholder="Your password"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        autoComplete="current-password"
                        required
                        aria-required="true"
                      />
                      <button
                        type="button"
                        className="sm-eye-btn"
                        onClick={() => setShowPass(v => !v)}
                        tabIndex={-1}
                        aria-label={showPass ? "Hide password" : "Show password"}
                      >
                        {showPass ? <IconEyeClosed /> : <IconEyeOpen />}
                      </button>
                    </div>
                  </div>

                  {/* Remember / Forgot */}
                  <div className="sm-meta">
                    <label className="sm-remember">
                      <input
                        type="checkbox"
                        checked={remember}
                        onChange={e => setRemember(e.target.checked)}
                      />
                      Remember me
                    </label>
                    <button
                      type="button"
                      className="sm-forgot-btn"
                      onClick={() => { setView("forgot"); setForgotError(""); }}
                    >
                      Forgot password?
                    </button>
                  </div>

                  {/* Submit */}
                  <button
                    className="sm-submit"
                    type="submit"
                    disabled={loading || isLoginLockedOut}
                  >
                    {loading && <span className="sm-spinner" />}
                    {isLoginLockedOut
                      ? `Locked — wait ${lockoutSecondsLeft}s`
                      : loading
                        ? "Signing in…"
                        : "Sign in"}
                  </button>

                </form>

                <div className="sm-card-footer">
                  No account yet?{" "}
                  <a onClick={() => navigate("/signup")}>Request access</a>
                </div>
              </>
            )}

            {/* ════════════════════════════
                VIEW: MFA
            ════════════════════════════ */}
            {view === "mfa" && (
              <>
                <button
                  type="button"
                  className="sm-back-btn"
                  onClick={() => { setPendingToken(null); setTotpCode(""); setMfaError(""); setView("login"); }}
                >
                  ← Back to login
                </button>

                <div className="sm-card-header">
                  <h2 className="sm-card-title">Two-factor authentication</h2>
                  <p className="sm-card-sub">Enter the 6-digit code from your authenticator app to continue.</p>
                </div>

                {mfaError && <div className="sm-error" role="alert">{mfaError}</div>}

                <form onSubmit={handleMfaVerify} noValidate>
                  <div className="sm-field">
                    <label className="sm-label" htmlFor="sm-totp">Authentication code</label>
                    <div className="sm-field-wrap">
                      <span className="sm-field-icon"><IconShield /></span>
                      <input
                        id="sm-totp"
                        className="sm-input"
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]{6}"
                        maxLength={6}
                        placeholder="000000"
                        value={totpCode}
                        onChange={e => setTotpCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        autoComplete="one-time-code"
                        required
                        style={{ letterSpacing: "6px", fontSize: "18px", fontWeight: 600, textAlign: "center" }}
                      />
                    </div>
                  </div>

                  <button
                    className="sm-submit"
                    type="submit"
                    disabled={loading || totpCode.length < 6}
                  >
                    {loading && <span className="sm-spinner" />}
                    {loading ? "Verifying…" : "Verify code"}
                  </button>
                </form>
              </>
            )}

            {/* ════════════════════════════
                VIEW: FORGOT PASSWORD
            ════════════════════════════ */}
            {view === "forgot" && (
              <>
                <button
                  type="button"
                  className="sm-back-btn"
                  onClick={() => { setView("login"); setForgotError(""); }}
                >
                  ← Back to login
                </button>

                <div className="sm-card-header">
                  <h2 className="sm-card-title">Reset your password</h2>
                  <p className="sm-card-sub">
                    Enter your email and we'll send a reset link if an account exists.
                  </p>
                </div>

                <div className="sm-divider">
                  <div className="sm-divider-line" />
                  <div className="sm-divider-label">enter your email</div>
                  <div className="sm-divider-line" />
                </div>

                {forgotError && <div className="sm-error" role="alert">{forgotError}</div>}

                <form onSubmit={handleForgotSubmit} noValidate>
                  <div className="sm-field">
                    <label className="sm-label" htmlFor="sm-forgot-email">Email address</label>
                    <div className="sm-field-wrap">
                      <span className="sm-field-icon"><IconEmail /></span>
                      <input
                        id="sm-forgot-email"
                        className="sm-input"
                        type="email"
                        placeholder="you@institution.edu"
                        value={forgotEmail}
                        onChange={e => setForgotEmail(e.target.value)}
                        autoComplete="email"
                        maxLength={254}
                        required
                      />
                    </div>
                  </div>

                  <button
                    className="sm-submit"
                    type="submit"
                    disabled={forgotLoading}
                  >
                    {forgotLoading && <span className="sm-spinner" />}
                    {forgotLoading ? "Sending…" : "Send reset link"}
                  </button>
                </form>
              </>
            )}

            {/* ════════════════════════════
                VIEW: FORGOT SENT
            ════════════════════════════ */}
            {view === "forgot-sent" && (
              <>
                <div className="sm-success-icon">
                  <svg
                    width="26" height="26" viewBox="0 0 24 24"
                    fill="none" stroke="#2EC4B6"
                    strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>

                <div className="sm-card-header">
                  <h2 className="sm-card-title">Check your email</h2>
                  <p className="sm-card-sub">
                    If an account exists for that email, a password reset link has been sent.
                    The link expires in 15 minutes.
                  </p>
                </div>

                <button
                  className="sm-submit"
                  type="button"
                  onClick={() => { setView("login"); setForgotEmail(""); }}
                >
                  Back to login
                </button>
              </>
            )}

          </div>
        </div>

      </div>
    </>
  );
}