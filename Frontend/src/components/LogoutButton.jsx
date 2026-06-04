import { useNavigate } from "react-router-dom";
import { useSession } from "../context/SessionContext";
const baseStyle = {
  display: "inline-flex",
  alignItems: "center",
  gap: 8,
  padding: "10px 20px",
  fontSize: 16,
  fontWeight: 600,
  fontFamily: "inherit",
  borderRadius: 10,
  cursor: "pointer",
  border: "1px solid #e5e7eb",
  background: "#fff",
  color: "#374151",
  transition: "background 0.15s, border-color 0.15s, color 0.15s",
};

const variantStyles = {
  default: {},
  dark: {
    background: "rgba(255,255,255,0.08)",
    borderColor: "rgba(255,255,255,0.18)",
    color: "rgba(255,255,255,0.88)",
  },
  counsellor: {
    borderColor: "#e8e8e8",
    color: "#666",
  },
};

export default function LogoutButton({ variant = "default", style = {}, label = "Log out" }) {
  const { logout, user } = useSession();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/", { replace: true });
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      title={user?.email ? `Sign out (${user.email})` : "Sign out"}
      style={{ ...baseStyle, ...variantStyles[variant], ...style }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = variant === "dark" ? "rgba(255,255,255,0.14)" : "#fef2f2";
        e.currentTarget.style.borderColor = variant === "dark" ? "rgba(255,255,255,0.28)" : "#fecaca";
        e.currentTarget.style.color = variant === "dark" ? "#fff" : "#dc2626";
      }}
      onMouseLeave={(e) => {
        Object.assign(e.currentTarget.style, {
          ...baseStyle,
          ...variantStyles[variant],
          ...style,
        });
      }}
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
        <polyline points="16 17 21 12 16 7" />
        <line x1="21" y1="12" x2="9" y2="12" />
      </svg>
      {label}
    </button>
  );
}
