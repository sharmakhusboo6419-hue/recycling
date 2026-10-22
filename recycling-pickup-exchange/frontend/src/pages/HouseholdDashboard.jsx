import { useEffect, useState } from "react";
import { api } from "../api";
import { useProfile } from "../profileContext";
import { useToast } from "../toastContext";
import RequestForm from "../components/RequestForm";
import RequestCard from "../components/RequestCard";
import LifecycleRail from "../components/LifecycleRail";
import QuantityComparison from "../components/QuantityComparison";
import { Empty, Hero, KpiStrip, matIcon, Skeletons } from "../components/ui";

// Household dashboard: new-request form + "my requests" list with detail modal.
export default function HouseholdDashboard() {
  const { profile } = useProfile();
  const toast = useToast();
  const [requests, setRequests] = useState(null);
  const [detail, setDetail] = useState(null);

  const load = () => {
    api.householdRequests(profile.id)
      .then(setRequests)
      .catch((e) => toast.error(e.message));
  };

  useEffect(() => {
    if (!profile || profile.role !== "household") return;
    load();
    // Light polling keeps the list in sync with collector activity.
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, [profile?.id, profile?.role]);

  if (!profile) return null;
  if (profile.role !== "household") {
    return <p className="center muted">This page is for households. Use "Switch profile" in the header.</p>;
  }

  const requestList = requests || [];
  const counts = {
    open: requestList.filter((request) => request.status === "Available").length,
    active: requestList.filter((request) => request.status === "Accepted").length,
    done: requestList.filter((request) => request.status === "Completed").length,
  };

  const openDetail = async (id) => {
    try {
      setDetail(await api.getRequest(id));
    } catch (e) {
      toast.error(e.message);
    }
  };

  const cancel = async (id) => {
    try {
      await api.cancelRequest(id, profile.id);
      toast.success("Request cancelled.");
      setDetail(null);
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <div className="dash">
      <Hero
        icon="🏠"
        chip={`Hi, ${profile.name.split(" ")[0]}`}
        title="My recycling pickups"
        subtitle="Post a pickup and nearby collectors claim it — you'll see who's coming and how the actual weight compares to your estimate."
      />

      <KpiStrip
        items={[
          { icon: "🟢", value: counts.open, label: "Open requests" },
          { icon: "🔵", value: counts.active, label: "Being picked up" },
          { icon: "✅", value: counts.done, label: "Completed" },
          { icon: "♻️", value: (requests || []).length, label: "Total posted" },
        ]}
      />

      <section className="card">
        <h2>➕ New pickup request</h2>
        <RequestForm householdId={profile.id} onCreated={() => { load(); toast.success("Pickup request posted!"); }} />
      </section>

      <section className="card">
        <h2>My requests</h2>
        {requests === null && <Skeletons count={3} />}
        {requests?.length === 0 && (
          <Empty icon="📦" title="No requests yet" hint="Post your first pickup request above — a nearby collector will claim it." />
        )}
        <div className="req-grid">
          {requests?.map((r) => (
            <RequestCard key={r.id} r={r} onOpen={() => openDetail(r.id)} />
          ))}
        </div>
      </section>

      {detail && (
        <div className="modal-backdrop" onClick={() => setDetail(null)}>
          <div className="modal card" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Request detail">
            <button className="close" onClick={() => setDetail(null)} aria-label="Close">✕</button>
            <h3>{detail.material_type} · {detail.estimated_weight_kg} kg</h3>
            <p className="muted">{detail.area}{detail.address_note ? ` — ${detail.address_note}` : ""}</p>
            <p>Status: <span className={`badge badge-${detail.status.toLowerCase()}`}>{detail.status}</span></p>
            {detail.collector && <p>Collector: <strong>{detail.collector.name}</strong> ({detail.collector.phone})</p>}
            <LifecycleRail request={detail} />
            {detail.collection_record && (
              <div className="variance-box">
                <QuantityComparison estimated={detail.estimated_weight_kg} actual={detail.collection_record.actual_weight_kg} compact />
                {detail.collection_record.notes && <p className="muted">Notes: {detail.collection_record.notes}</p>}
              </div>
            )}
            {detail.status === "Available" && (
              <button className="danger" onClick={() => cancel(detail.id)}>Cancel request</button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
