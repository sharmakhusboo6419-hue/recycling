import { NavLink, useNavigate } from "react-router-dom";
import { useProfile } from "../profileContext";

// App header with brand + visible profile switcher (demo-friendly).
export default function Header() {
  const { profile } = useProfile();
  const navigate = useNavigate();

  return (
    <header className="header">
      <NavLink to="/" className="brand">
        <span className="brand-mark" aria-hidden="true">↻</span>
        <span>Loop Local</span>
      </NavLink>
      <nav className="nav" aria-label="Main">
        {profile?.role === "household" && (
          <NavLink to="/" end className={({ isActive }) => (isActive ? "on" : "")}>My requests</NavLink>
        )}
        {profile?.role === "collector" && (
          <>
            <NavLink to="/" end className={({ isActive }) => (isActive ? "on" : "")}>Dashboard</NavLink>
            <NavLink to="/profile" className={({ isActive }) => (isActive ? "on" : "")}>My profile</NavLink>
          </>
        )}
        {profile && <NavLink to="/stats" className={({ isActive }) => (isActive ? "on" : "")}>Impact</NavLink>}
      </nav>
      {profile ? (
        <button className="switch" onClick={() => navigate("/switch")} title="Switch profile">
          <span className="avatar" aria-hidden>{profile.role === "household" ? "🏠" : "🚛"}</span>
          {profile.name} <span style={{ opacity: 0.6, fontWeight: 500 }}>· switch</span>
        </button>
      ) : (
        <button className="switch" onClick={() => navigate("/switch")}>Continue as…</button>
      )}
    </header>
  );
}
