import { useEffect, useState } from "react";
import { api } from "../api";
import { useToast } from "../toastContext";

// Summary stats with plain-CSS bar chart (no chart dependency needed).
const STATUS_COLORS = {
  Available: "#3d8f57",
  Accepted: "#2f6fb0",
  Completed: "#2e7d43",
  Cancelled: "#a08b3a",
  Failed: "#c64544",
};

export default function Stats() {
  const toast = useToast();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.stats().then(setStats).catch((e) => toast.error(e.message));
  }, []);

  if (!stats) return <p className="muted center">Loading stats…</p>;

  const materials = Object.entries(stats.total_actual_kg_by_material).filter(([, v]) => v > 0);
  const maxKg = Math.max(1, ...materials.map(([, v]) => v));
  const totalStatus = Object.values(stats.status_counts).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="dash">
      <section className="card">
        <h2>📊 Summary</h2>
        <div className="stat-cards">
          <div className="stat">
            <strong>{stats.total_completed}</strong>
            <span>Completed pickups</span>
          </div>
          <div className="stat">
            <strong>{stats.average_variance_percent === null ? "—" : `${stats.average_variance_percent}%`}</strong>
            <span>Avg variance</span>
          </div>
          <div className="stat">
            <strong>{stats.matching_accuracy_percent}%</strong>
            <span>Matching accuracy (±10%)</span>
          </div>
          <div className="stat">
            <strong>{Object.values(stats.status_counts).reduce((a, b) => a + b, 0)}</strong>
            <span>Total requests</span>
          </div>
        </div>
      </section>

      <section className="card">
        <h2>Requests by status</h2>
        <div className="bars">
          {Object.entries(stats.status_counts).map(([k, v]) => (
            <div className="bar-row" key={k}>
              <span className="bar-label">{k}</span>
              <div className="bar-track">
                <div className="bar-fill" style={{
                  width: `${(v / totalStatus) * 100}%`,
                  background: STATUS_COLORS[k],
                }} />
              </div>
              <span className="bar-value">{v}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <h2>Actual kg collected by material</h2>
        {materials.length === 0 && <p className="muted">No completed pickups with records yet.</p>}
        <div className="bars">
          {materials.map(([k, v]) => (
            <div className="bar-row" key={k}>
              <span className="bar-label">{k}</span>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${(v / maxKg) * 100}%`, background: "#3d8f57" }} />
              </div>
              <span className="bar-value">{v} kg</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
