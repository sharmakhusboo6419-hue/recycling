// Shared request card with colour-coded status badge.
export default function RequestCard({ r, onOpen, children }) {
  return (
    <article className="req-card">
      <header>
        <strong>{r.material_type}</strong>
        <span className={`badge badge-${r.status.toLowerCase()}`}>{r.status}</span>
      </header>
      <p className="muted">{r.area} · {r.estimated_weight_kg} kg · {new Date(r.created_at).toLocaleDateString()}</p>
      {children}
      {onOpen && <button onClick={onOpen} className="ghost">Details</button>}
    </article>
  );
}
