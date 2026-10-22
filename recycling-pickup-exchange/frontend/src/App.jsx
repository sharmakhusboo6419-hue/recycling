import { Navigate, Route, Routes } from "react-router-dom";
import { useProfile } from "./profileContext";
import Header from "./components/Header";
import ProfilePicker from "./pages/ProfilePicker";
import HouseholdDashboard from "./pages/HouseholdDashboard";
import CollectorDashboard from "./pages/CollectorDashboard";
import CollectorProfile from "./pages/CollectorProfile";
import Stats from "./pages/Stats";

export default function App() {
  const { profile } = useProfile();

  const home = !profile
    ? <ProfilePicker />
    : profile.role === "household"
      ? <HouseholdDashboard />
      : <CollectorDashboard />;

  return (
    <div className="app">
      <Header />
      <main>
        <Routes>
          <Route path="/" element={home} />
          <Route path="/switch" element={<ProfilePicker />} />
          <Route path="/stats" element={profile ? <Stats /> : <Navigate to="/switch" replace />} />
          <Route path="/profile" element={profile ? <CollectorProfile /> : <Navigate to="/switch" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="footer muted">
        Team Nexora · Tech Fusion 2026 · Recycling Pickup Exchange prototype
      </footer>
    </div>
  );
}
