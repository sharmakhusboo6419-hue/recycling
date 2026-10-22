const STEPS = ["Available", "Accepted", "Completed"];

function stamp(value) {
  return value ? new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : null;
}

/** A compact, text-supported record of the dispatch state for a pickup. */
export default function LifecycleRail({ request }) {
  const terminal = ["Cancelled", "Failed"].includes(request.status);
  const completeIndex = STEPS.indexOf(request.status);
  const reason = request.status === "Cancelled" ? request.cancel_reason : request.failure_reason;
  const times = [request.created_at, request.accepted_at, request.completed_at];

  return (
    <section className={`lifecycle-rail ${terminal ? "is-terminal" : ""}`} aria-label={`Pickup lifecycle: ${request.status}`}>
      <div className="lifecycle-label"><span aria-hidden="true">⌁</span> Verification trail</div>
      <ol>
        {STEPS.map((step, i) => {
          const reached = !terminal && (completeIndex >= i || (request.status === "Available" && i === 0));
          return <li key={step} className={reached ? "reached" : ""}>
            <span className="trail-mark" aria-hidden="true">{reached ? "✓" : i + 1}</span>
            <span><b>{step}</b>{reached && stamp(times[i]) && <small>{stamp(times[i])}</small>}</span>
          </li>;
        })}
      </ol>
      {terminal && <p className="terminal-note"><b>{request.status}:</b> {reason || "No reason recorded."}</p>}
    </section>
  );
}
