// Shared dashboard building blocks: hero, KPI strip, empty states, skeletons,
// status/material metadata used across the household and collector views.

export const STATUS_META = {
  Available: { icon: "🟢", color: "#3fae63", label: "Open for claims" },
  Accepted: { icon: "🔵", color: "#2f6fb0", label: "Claimed — pickup pending" },
  Completed: { icon: "✅", color: "#2e7d43", label: "Collected & verified" },
  Cancelled: { icon: "🟡", color: "#a9862e", label: "Cancelled" },
  Failed: { icon: "🔴", color: "#c94a49", label: "Pickup failed" },
};

export const MATERIAL_ICONS = {
  Paper: "📄",
  Plastic: "🥤",
  Metal: "🥫",
  Glass: "🫙",
  "E-waste": "🔌",
  Cardboard: "📦",
  Mixed: "🗑️",
};

export const matIcon = (m) => MATERIAL_ICONS[m] || "♻️";
export const statusMeta = (s) => STATUS_META[s] || { icon: "♻️", color: "#3fae63", label: s };

/** Gradient hero banner shown at the top of every dashboard. */
export function Hero({ icon, chip, title, subtitle, children }) {
  return (
    <section className="hero">
      {chip && <span className="hero-chip">{chip}</span>}
      <div className="hero-icon" aria-hidden>{icon}</div>
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
      {children}
    </section>
  );
}

/** KPI strip: array of {icon, value, label}. */
export function KpiStrip({ items }) {
  return (
    <div className="kpi-grid">
      {items.map((k) => (
        <div className="kpi" key={k.label}>
          <span className="kpi-ico" aria-hidden>{k.icon}</span>
          <div>
            <strong>{k.value}</strong>
            <span>{k.label}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/** Friendly empty state. */
export function Empty({ icon = "🌱", title, hint }) {
  return (
    <div className="empty">
      <span className="empty-ico" aria-hidden>{icon}</span>
      <strong>{title}</strong>
      {hint && <p className="muted" style={{ margin: "0.3rem 0 0" }}>{hint}</p>}
    </div>
  );
}

/** Loading skeletons. */
export function Skeletons({ count = 3 }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => <div className="skeleton" key={i} />)}
    </>
  );
}

/** Conic-gradient donut/ring chart (pure CSS, no dependencies). */
export function Donut({ value, max, color = "#3fae63", center, sub }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  const deg = Math.round(pct * 3.6);
  return (
    <div className="donut-wrap">
      <div
        className="donut"
        style={{ background: `conic-gradient(${color} ${deg}deg, #e6f0e8 ${deg}deg 360deg)` }}
        role="img"
        aria-label={`${pct}%`}
      >
        <div className="donut-inner">
          <strong>{center}</strong>
          <span>{sub}</span>
        </div>
      </div>
    </div>
  );
}

/** Variance delta pill: green within ±10%, amber ±25%, red beyond. */
export function VarianceDelta({ percent }) {
  const abs = Math.abs(percent);
  const cls = abs <= 10 ? "good" : abs <= 25 ? "warn" : "bad";
  const face = cls === "good" ? "🎯" : cls === "warn" ? "🤏" : "📉";
  return (
    <span className={`variance-delta ${cls}`}>
      {face} {percent > 0 ? "+" : ""}{percent}% vs estimate
    </span>
  );
}
