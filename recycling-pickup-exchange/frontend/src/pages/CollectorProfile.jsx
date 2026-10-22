import { useEffect, useState } from "react";
import { api } from "../api";
import { useProfile } from "../profileContext";
import { useToast } from "../toastContext";
import { MATERIALS } from "../api";

// Collector profile page: edit accepted materials / service areas / capacity.
export default function CollectorProfile() {
  const { profile, setProfile } = useProfile();
  const toast = useToast();
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (profile?.role !== "collector") return;
    api.getCollector(profile.id).then((c) =>
      setForm({
        name: c.name,
        phone: c.phone,
        accepted_materials: c.accepted_materials,
        service_areas: c.service_areas.join(", "),
        max_capacity_kg: c.max_capacity_kg ?? "",
        active: c.active,
      })
    ).catch((e) => toast.error(e.message));
  }, [profile?.id]);

  if (!profile || profile.role !== "collector") {
    return <p className="center muted">Collector profile page — switch to a collector profile first.</p>;
  }
  if (!form) return <p className="muted">Loading…</p>;

  const toggleMaterial = (m) =>
    setForm((f) => ({
      ...f,
      accepted_materials: f.accepted_materials.includes(m)
        ? f.accepted_materials.filter((x) => x !== m)
        : [...f.accepted_materials, m],
    }));

  const save = async (e) => {
    e.preventDefault();
    const areas = form.service_areas.split(",").map((s) => s.trim()).filter(Boolean);
    if (!form.accepted_materials.length) return toast.error("Pick at least one material.");
    if (!areas.length) return toast.error("At least one service area is required.");
    setBusy(true);
    try {
      const updated = await api.updateCollector(profile.id, {
        name: form.name,
        phone: form.phone,
        accepted_materials: form.accepted_materials,
        service_areas: areas,
        max_capacity_kg: form.max_capacity_kg ? Number(form.max_capacity_kg) : null,
        active: form.active,
      });
      setProfile({ ...profile, ...updated, role: "collector" });
      toast.success("Profile saved.");
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="dash">
      <section className="dashboard-intro">
        <div><div className="eyebrow">Collector settings</div><h1>Fine-tune your local route.</h1><p>Keep your coverage and accepted materials up to date so the right pickups find you.</p></div>
        <div className="dispatch-note"><strong>Matching matters</strong><span>Active collectors receive requests aligned with their areas and materials.</span></div>
      </section>
      <section className="card narrow">
        <div className="section-heading"><h2>Collector profile</h2><p className="muted">Your availability and coverage.</p></div>
        <form className="req-form" onSubmit={save}>
          <label>Name <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
          <label>Phone <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
          <fieldset>
            <legend>Accepted materials</legend>
            <div className="chip-row">
              {MATERIALS.map((m) => (
                <button type="button" key={m}
                  className={`chip ${form.accepted_materials.includes(m) ? "chip-on" : ""}`}
                  onClick={() => toggleMaterial(m)}>{m}</button>
              ))}
            </div>
          </fieldset>
          <label>Service areas (comma-separated)
            <input value={form.service_areas}
              onChange={(e) => setForm({ ...form, service_areas: e.target.value })} />
          </label>
          <label>Max capacity kg (optional)
            <input type="number" min="1" max="1000" value={form.max_capacity_kg}
              onChange={(e) => setForm({ ...form, max_capacity_kg: e.target.value })} />
          </label>
          <label className="check">
            <input type="checkbox" checked={form.active}
              onChange={(e) => setForm({ ...form, active: e.target.checked })} />
            Active (eligible to receive matches)
          </label>
          <button className="primary" type="submit" disabled={busy}>{busy ? "Saving…" : "Save profile"}</button>
        </form>
      </section>
    </div>
  );
}
