import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useProfile } from "../profileContext";
import { useToast } from "../toastContext";
import RequestCard from "../components/RequestCard";
import QuantityComparison from "../components/QuantityComparison";
import { Empty, Hero, KpiStrip, Skeletons, VarianceDelta } from "../components/ui";

// Collector dashboard: tabs for available / accepted / history + actions.
export default function CollectorDashboard() {
  const { profile } = useProfile();
  const toast = useToast();
  const [tab, setTab] = useState("available");
  const [items, setItems] = useState(null);
  const [completing, setCompleting] = useState(null); // request being completed
  const [failing, setFailing] = useState(null);       // request failing w/ reason
  const [actual, setActual] = useState("");
  const [notes, setNotes] = useState("");
  const [reason, setReason] = useState("");
  const [counts, setCounts] = useState({ available: null, accepted: null, history: null });

  const load = useCallback(() => {
    if (!profile || profile.role !== "collector") return;
    Promise.all([api.availableRequests(profile.id), api.collectorRequests(profile.id)])
      .then(([available, history]) => {
        setCounts({
          available: available.length,
          accepted: history.filter((request) => request.status === "Accepted").length,
          history: history.length,
        });
        setItems(tab === "available"
          ? available
          : tab === "accepted"
            ? history.filter((request) => request.status === "Accepted")
            : history);
      })
      .catch((e) => toast.error(e.message));
  }, [profile?.id, profile?.role, tab]);

  useEffect(() => {
    load();
    const t = setInterval(load, 10000); // poll every ~10s
    return () => clearInterval(t);
  }, [load]);

  if (!profile) return null;
  if (profile.role !== "collector") {
    return <p className="center muted">This page is for collectors. Use "Switch profile" in the header.</p>;
  }

  const act = async (fn, successMsg) => {
    try {
      await fn();
      toast.success(successMsg);
      setCompleting(null);
      setFailing(null);
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const claim = async (id) => {
    try {
      await api.claim(id, profile.id);
      toast.success("Request secured. It is now assigned to your route.");
    } catch (e) {
      if (e.status === 409) toast.error("Another collector just secured this pickup. The live queue has been refreshed.");
      else toast.error(e.message);
    } finally {
      load();
    }
  };

  return (
    <div className="dash">
      <Hero
        icon="🚛"
        chip={`Hi, ${profile.name.split(" ")[0]}`}
        title="Collector dispatch board"
        subtitle={`Open pickups matching ${profile.service_areas?.join(" · ") || "your service areas"} — claim one and record the collected weight when done.`}
      />

      <KpiStrip
        items={[
          { icon: "🟢", value: counts.available ?? "—", label: "Open for me" },
          { icon: "🔵", value: counts.accepted ?? "—", label: "My accepted" },
          { icon: "🗂️", value: counts.history ?? "—", label: "My history" },
          { icon: "🧭", value: profile.service_areas?.length || "—", label: "Service areas" },
        ]}
      />

      <div className="tabs" role="tablist" aria-label="Collector views">
        {[["available", "Available for me"], ["accepted", "My accepted"], ["history", "History"]].map(([k, label]) => (
          <button key={k} role="tab" aria-selected={tab === k}
            className={tab === k ? "active" : ""} onClick={() => setTab(k)}>
            {label}
            {counts[k] != null && <span className="tab-count">{counts[k]}</span>}
          </button>
        ))}
      </div>

      {items === null && <Skeletons count={3} />}
      {items?.length === 0 && (
        <Empty
          icon={tab === "available" ? "📭" : "🗂️"}
          title={tab === "available" ? "No matching pickups right now" : "Nothing here yet"}
          hint={tab === "available"
            ? "New requests matching your materials & areas appear here automatically (refresh every 10s)."
            : "Claimed pickups will show up in this tab."}
        />
      )}

      <div className="req-grid">
        {items?.map((r) => (
          <RequestCard key={r.id} r={r}>
            {tab === "available" && r.status === "Available" && (
              <button className="primary" onClick={() => claim(r.id)}>Claim</button>
            )}
            {tab === "accepted" && r.status === "Accepted" && (
              <div className="row">
                <button className="primary" onClick={() => { setCompleting(r); setActual(""); setNotes(""); }}>
                  Complete
                </button>
                <button className="danger" onClick={() => { setFailing(r); setReason(""); }}>Fail</button>
                <button className="ghost" onClick={() =>
                  act(() => api.collectorCancel(r.id, profile.id, "Cancelled by collector"), "Request cancelled.")}>
                  Cancel
                </button>
              </div>
            )}
            {tab === "history" && r.collection_record && (
              <p className="muted">
                Actual: {r.collection_record.actual_weight_kg} kg · variance {r.collection_record.variance_percent}%
              </p>
            )}
          </RequestCard>
        ))}
      </div>

      {completing && (
        <div className="modal-backdrop" onClick={() => setCompleting(null)}>
          <div className="modal card" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Complete pickup">
            <h3>Record collected quantity</h3>
            <p className="muted">{completing.material_type} · estimated {completing.estimated_weight_kg} kg</p>
            <label>Actual weight (kg)
              <input type="number" step="0.1" min="0.1" max="1000" value={actual}
                onChange={(e) => setActual(e.target.value)} autoFocus />
            </label>
            <QuantityComparison estimated={completing.estimated_weight_kg} actual={actual} />
            <label>Notes (optional)
              <input value={notes} onChange={(e) => setNotes(e.target.value)} />
            </label>
            <div className="row">
              <button className="primary" onClick={() => {
                const w = Number(actual);
                if (!actual || Number.isNaN(w) || w <= 0 || w > 1000) {
                  toast.error("Enter an actual weight between 0 and 1000 kg.");
                  return;
                }
                act(() => api.complete(completing.id, profile.id, w, notes), "Pickup completed — variance recorded.");
              }}>Confirm completion</button>
              <button onClick={() => setCompleting(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {failing && (
        <div className="modal-backdrop" onClick={() => setFailing(null)}>
          <div className="modal card" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Mark failed">
            <h3>Mark pickup as failed</h3>
            <label>Reason
              <input value={reason} onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Household not reachable" autoFocus />
            </label>
            <div className="row">
              <button className="danger" onClick={() => {
                if (!reason.trim()) { toast.error("A reason is required."); return; }
                act(() => api.fail(failing.id, profile.id, reason), "Marked as failed.");
              }}>Mark failed</button>
              <button onClick={() => setFailing(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
