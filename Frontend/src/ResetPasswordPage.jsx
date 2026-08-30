// BACKEND CONTRACT FOR FORGOT PASSWORD (frontend depends on these):
// POST /api/auth/forgot-password
//   - MUST always return HTTP 200 with { "message": "ok" } — even if email not found
//   - Token must be: cryptographically random (secrets.token_urlsafe(32)), single-use,
//     expire in 15 minutes, stored hashed in DB (not plaintext)
//   - Rate limit: max 3 requests per email per hour on the backend as well
//   - Email must contain: reset link with token as query param, expiry warning, "if you
//     didn't request this, ignore this email" notice
//   - Audit log: log FORGOT_PASSWORD_REQUEST (INFO) and PASSWORD_RESET_SUCCESS (WARNING)
//
// POST /api/auth/reset-password
//   - Body: { token: string, new_password: string }
//   - Validate token: exists, not expired, not already used — return 400 with
//     "Invalid or expired token." for all failure cases (don't distinguish between them)
//   - On success: hash new password (bcrypt 12 rounds), invalidate ALL existing sessions
//     for that user (revoke all refresh tokens), mark token as used
//   - Return HTTP 200 { "message": "Password reset successfully." }

import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { resetPassword } from "./services/authApi";
import hope from "./assets/hope.jpg";
import logo from "./assets/logo.png";

// SECURITY: token is read from the query string once, then stripped from the URL
// via replaceState so it does not persist in browser history.
function readResetTokenFromQuery() {
  const params = new URLSearchParams(window.location.search);
  return (params.get("token") || "").trim();
}

function stripTokenFromUrl() {
  if (!window.location.search) return;
  window.history.replaceState(null, "", window.location.pathname);
}

const SAFE_API_ERRORS = new Set([
  "Invalid or expired token.",
  "Token already used.",
  "Reset failed.",
]);

const HAS_UPPER = /[A-Z]/;
const HAS_LOWER = /[a-z]/;
const HAS_DIGIT = /[0-9]/;
const HAS_SPECIAL = /[!@#$%^&*(),.?":{}|<>]/;

function getPasswordRuleErrors(password, confirm) {
  const errors = [];
  if (password.length < 10) errors.push("Password must be at least 10 characters.");
  if (!HAS_UPPER.test(password)) errors.push("Must include an uppercase letter.");
  if (!HAS_LOWER.test(password)) errors.push("Must include a lowercase letter.");
  if (!HAS_DIGIT.test(password)) errors.push("Must include a number.");
  if (!HAS_SPECIAL.test(password)) errors.push("Must include a special character.");
  if (password !== confirm) errors.push("Passwords do not match.");
  return errors;
}

function countPassingRules(password) {
  let n = 0;
  if (password.length >= 10) n += 1;
  if (HAS_UPPER.test(password)) n += 1;
  if (HAS_LOWER.test(password)) n += 1;
  if (HAS_DIGIT.test(password)) n += 1;
  if (HAS_SPECIAL.test(password)) n += 1;
  return n;
}

function getStrengthLevel(password) {
  if (password.length < 10) return { label: "Weak", bars: 1, color: "#ff6b6b" };
  const passing = countPassingRules(password);
  if (passing <= 2) return { label: "Fair", bars: 2, color: "#f5a623" };
  if (passing <= 4) return { label: "Strong", bars: 3, color: "#3dd6d0" };
  return { label: "Very strong", bars: 4, color: "#4ade80" };
}

function StrengthIndicator({ password }) {
  const { label, bars, color } = getStrengthLevel(password);
  return (
    <div style={{ marginTop: 8, marginBottom: 4 }}>
      <div style={{ display: "flex", gap: 6, marginBottom: 6 }}>
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: 4,
              borderRadius: 2,
              background: i <= bars ? color : "rgba(255,255,255,0.12)",
              transition: "background 0.2s",
            }}
          />
        ))}
      </div>
      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>{label}</div>
    </div>
  );
}

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [token] = useState(() => readResetTokenFromQuery());
  const tokenMissing = !token;

  useEffect(() => {
    if (token) stripTokenFromUrl();
  }, [token]);

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [validationErrors, setValidationErrors] = useState([]);
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [resetCompleted, setResetCompleted] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (tokenMissing || resetCompleted) return;

    const errors = getPasswordRuleErrors(password, confirm);
    if (errors.length) {
      setValidationErrors(errors);
      setApiError("");
      return;
    }

    setValidationErrors([]);
    setApiError("");
    setLoading(true);

    try {
      await resetPassword(token.trim(), password);
      setResetCompleted(true);
      setPassword("");
      setConfirm("");
      setSuccess(true);
    } catch (err) {
      const msg = err?.message || "";
      if (SAFE_API_ERRORS.has(msg)) {
        setApiError(msg);
      } else {
        setApiError("Reset failed. The link may have expired.");
      }
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
        .lp-root {
          position: relative; height: 100vh; width: 100vw;
          overflow: hidden; font-family: 'Inter', sans-serif;
          display: flex; align-items: center; justify-content: center;
        }
        .lp-bg { position: absolute; inset: 0; background-size: cover; background-position: center; }
        .lp-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.42); }
        .lp-card {
          position: relative; z-index: 2;
          width: 420px; max-width: calc(100vw - 48px);
          background: rgba(28,30,38,0.82); backdrop-filter: blur(28px);
          border-radius: 20px; border: 1px solid rgba(255,255,255,0.12);
          padding: 44px 40px 38px; color: #fff;
        }
        .lp-card-title { font-size: 24px; font-weight: 700; margin-bottom: 6px; }
        .lp-card-sub { font-size: 14px; color: rgba(255,255,255,0.50); margin-bottom: 24px; line-height: 1.6; }
        .lp-field { margin-bottom: 14px; }
        .lp-input {
          width: 100%; padding: 13px 14px;
          background: rgba(255,255,255,0.09); border: 1px solid rgba(255,255,255,0.14);
          border-radius: 10px; color: #fff; font-size: 15px;
          font-family: 'Inter', sans-serif; outline: none;
        }
        .lp-input:focus { border-color: rgba(61,214,208,0.5); }
        .lp-error {
          font-size: 13px; color: #ff9090;
          background: rgba(255,60,60,0.10); border: 1px solid rgba(255,60,60,0.22);
          border-radius: 9px; padding: 10px 14px; margin-bottom: 16px; line-height: 1.5;
        }
        .lp-validation-list {
          font-size: 13px; color: #ff9090;
          background: rgba(255,60,60,0.10); border: 1px solid rgba(255,60,60,0.22);
          border-radius: 9px; padding: 10px 14px 10px 28px; margin-bottom: 16px;
          line-height: 1.6;
        }
        .lp-btn {
          width: 100%; padding: 14px;
          background: linear-gradient(135deg, #4a8a94 0%, #3dd6d0 100%);
          border: none; border-radius: 10px; color: #fff;
          font-size: 15px; font-weight: 600; font-family: 'Inter', sans-serif;
          cursor: pointer; margin-bottom: 12px;
        }
        .lp-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .lp-link { color: #7ad4ff; text-decoration: none; font-size: 14px; }
        .lp-link:hover { color: #b8e8ff; text-decoration: underline; }
      `}</style>

      <div className="lp-root">
        <div className="lp-bg" style={{ backgroundImage: `url(${hope})` }} />
        <div className="lp-overlay" />

        <div className="lp-card">
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 22 }}>
            <img src={logo} alt="Sentio Mind" style={{ width: 46, height: 46, objectFit: "contain", borderRadius: 10 }} />
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: 26, fontWeight: 700 }}>
              <span style={{ color: "#7ffff4" }}>Sentio </span>
              <span style={{ color: "#a0f0e8" }}>Mind</span>
            </span>
          </div>

          {tokenMissing ? (
            <>
              <div className="lp-error">Invalid or expired reset link.</div>
              <Link to="/" className="lp-link">Back to login</Link>
            </>
          ) : resetCompleted && !success ? (
            <>
              <div className="lp-error">This reset link has already been used.</div>
              <Link to="/" className="lp-link">Back to login</Link>
            </>
          ) : success ? (
            <div style={{ textAlign: "center" }}>
              <div className="lp-card-title" style={{ marginBottom: 12 }}>
                Password reset successfully. You can now log in.
              </div>
              <button className="lp-btn" type="button" onClick={() => navigate("/")}>
                Go to login
              </button>
            </div>
          ) : (
            <>
              <div className="lp-card-title">Set a new password</div>
              <div className="lp-card-sub">Choose a strong password for your account.</div>

              {resetCompleted && (
                <div className="lp-error">This reset link has already been used.</div>
              )}

              <form onSubmit={handleSubmit}>
                <div className="lp-field">
                  <input
                    className="lp-input"
                    type="password"
                    placeholder="New password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                    maxLength={128}
                    required
                  />
                  <StrengthIndicator password={password} />
                </div>

                <div className="lp-field">
                  <input
                    className="lp-input"
                    type="password"
                    placeholder="Confirm new password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    autoComplete="new-password"
                    maxLength={128}
                    required
                  />
                </div>

                {validationErrors.length > 0 && (
                  <ul className="lp-validation-list">
                    {validationErrors.map((msg) => (
                      <li key={msg}>{msg}</li>
                    ))}
                  </ul>
                )}

                {apiError && <div className="lp-error">{apiError}</div>}

                <button className="lp-btn" type="submit" disabled={loading || resetCompleted}>
                  {loading ? "Resetting…" : "Reset password"}
                </button>
              </form>

              <Link to="/" className="lp-link">Back to login</Link>
            </>
          )}
        </div>
      </div>
    </>
  );
}
