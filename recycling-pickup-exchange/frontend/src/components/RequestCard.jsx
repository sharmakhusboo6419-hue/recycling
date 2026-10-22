import LifecycleRail from "./LifecycleRail";
import { matIcon, statusMeta } from "./ui";

// Shared request card with colour-coded status badge, material icon and lifecycle clarity.
export default function RequestCard({ r, onOpen, children }) {
  const meta = statusMeta(r.status);
  return (
    <article className={`req-card st-${r.status.toLowerCase()}`}>
      <header>
        <span className="mat-line">
          <span className="mat-ico" aria-hidden="true">{matIcon(r.material_type)}</span>
          <strong>{r.material_type}</strong>
        </span>
        <span className={`badge badge-${r.status.toLowerCase()}`} title={meta.label}>
          {meta.icon} {r.status}
        </span>
      </header>
      <div className="req-meta">
        <span className="meta-pill">📍 {r.area}</span>
        <span className="meta-pill">⚖️ {r.estimated_weight_kg} kg</span>
        <span className="meta-pill">🗓 {new Date(r.created_at).toLocaleDateString()}</span>
      </div>
      <LifecycleRail request={r} />
      {children}
      {onOpen && <button onClick={onOpen} className="ghost">Details</button>}
    </article>
  );
}
