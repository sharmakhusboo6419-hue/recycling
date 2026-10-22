function format(value) {
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export default function QuantityComparison({ estimated, actual, compact = false }) {
  const entered = actual !== "" && actual !== null && actual !== undefined && !Number.isNaN(Number(actual));
  if (!entered) return null;
  const difference = Number(actual) - Number(estimated);
  const percent = Number(estimated) ? (difference / Number(estimated)) * 100 : 0;
  const direction = difference === 0 ? "exactly as estimated" : `${format(Math.abs(difference))} kg ${difference > 0 ? "more" : "less"}`;
  return (
    <div className={`quantity-comparison ${difference === 0 ? "is-exact" : difference > 0 ? "is-more" : "is-less"}`}>
      <div className="quantity-stamp" aria-hidden="true">{difference === 0 ? "=" : difference > 0 ? "+" : "−"}</div>
      <div>
        <p className="quantity-kicker">{compact ? "Recorded quantity" : "Live verification"}</p>
        <strong>{format(actual)} kg <span>actual</span></strong>
        <p>{format(estimated)} kg estimated · <b>{direction}</b> ({difference >= 0 ? "+" : ""}{format(percent)}%)</p>
      </div>
    </div>
  );
}
