import { useEffect, useState } from "react";
import { api } from "../api";
import { useToast } from "../toastContext";
import { Donut, Hero, KpiStrip, Skeletons, STATUS_META } from "../components/ui";

export default function Stats() {
  const toast = useToast();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.stats().then(setStats).catch((e) => toast.error(e.message));
  }, [toast]);

  if (!stats) return <div className="dash"><Skeletons count={2} /></div>;

  const materials = Object.entries(stats.total_actual_kg_by_material).filter(([, v]) => v > 0);
  const maxKg = Math.max(1, ...materials.map(([, v]) => v));
  const totalStatus = Object.values(stats.status_counts).reduce((a, b) => a + b, 0) || 1;
  const done = stats.status_counts.Completed || 0;

  return (
    <div className="dash">
      <Hero
        icon="🌍"
        chip="Team Nexora"
        title="Impact dashboard"
        subtitle="Live totals for the whole exchange — collected volume, estimate accuracy and request flow."
      />

      <KpiStrip
        items={[
          { icon: "♻️", value: stats.total_completed, label: "Completed pickups" },
          { icon: "⚖️", value: `${materials.reduce((a, [, v]) => a + v, 0).toFixed(1)} kg`, label: "Total collected" },
          {
            icon: "🎯",
            value: stats.average_variance_percent === null ? "—" : `${stats.average_variance_percent}%`,
            label: "Avg variance",
          },
          { icon: "🤝", value: `${stats.matching_accuracy_percent}%`, label: "Matching accuracy ±10%" },
        ]}
      />

      <section className="card">
        <h2>Request flow</h2>
        <div className="donut-wrap">
          <Donut
            value={done}
            max={totalStatus}
            color="#2e7d43"
            center={`${Math.round((done / totalStatus) * 100)}%`}
            sub="completed"
          />
          <div className="bars" style={{ flex: 1, minWidth: "15rem" }}>
            {Object.entries(stats.status_counts).map(([k, v]) => (
              <div className="bar-row" key={k}>
                <span className="bar-label">{STATUS_META[k]?.icon} {k}</span>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{ width: `${(v / totalStatus) * 100}%`, background: STATUS_META[k]?.color }}
                  />
                </div>
                <span className="bar-value">{v}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="card">
        <h2>Collected kg by material</h2>
        {materials.length === 0 && <p className="muted">No completed pickups with records yet.</p>}
        <div className="bars">
          {materials.map(([k, v]) => (
            <div className="bar-row" key={k}>
              <span className="bar-label">{k}</span>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${(v / maxKg) * 100}%`, background: "#2e7d43" }} />
              </div>
              <span className="bar-value">{v} kg</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
