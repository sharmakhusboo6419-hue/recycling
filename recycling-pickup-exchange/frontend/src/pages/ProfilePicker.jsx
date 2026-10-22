import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, MATERIALS } from "../api";
import { useProfile } from "../profileContext";
import { useToast } from "../toastContext";
import "./picker.css";

// "Continue as…" screen shown on first load (and via Switch profile).
// Choose a role, pick a seeded profile, or create a new one.
const BENGALURU_AREAS = ["Koramangala", "Indiranagar", "Whitefield", "Jayangar", "HSR Layout", "BTM Layout"];

export default function ProfilePicker() {
  const { setProfile } = useProfile();
  const toast = useToast();
  const navigate = useNavigate();
  const [role, setRole] = useState("household");
  const [households, setHouseholds] = useState([]);
  const [collectors, setCollectors] = useState([]);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);

  // create-form state
  const [form, setForm] = useState({ name: "", phone: "", area: "", materials: [], serviceAreas: "", capacity: "" });

  useEffect(() => {
    api.households().then(setHouseholds).catch((e) => toast.error(e.message));
    api.collectors().then(setCollectors).catch((e) => toast.error(e.message));
  }, []);

  const pick = (p) => {
    setProfile({ role, ...p });
    navigate("/");
  };

  const toggleMaterial = (m) =>
    setForm((f) => ({
      ...f,
      materials: f.materials.includes(m) ? f.materials.filter((x) => x !== m) : [...f.materials, m],
    }));

  const create = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.phone.trim()) {
      toast.error("Name and phone are required.");
      return;
    }
    setBusy(true);
    try {
      let p;
      if (role === "household") {
        if (!form.area.trim()) throw new Error("Area is required for a household.");
        p = await api.createHousehold({ name: form.name, phone: form.phone, area: form.area });
      } else {
        const areas = form.serviceAreas.split(",").map((s) => s.trim()).filter(Boolean);
        if (!form.materials.length) throw new Error("Pick at least one accepted material.");
        if (!areas.length) throw new Error("At least one service area is required.");
        p = await api.createCollector({
          name: form.name,
          phone: form.phone,
          accepted_materials: form.materials,
          service_areas: areas,
          max_capacity_kg: form.capacity ? Number(form.capacity) : null,
        });
      }
      toast.success(`Welcome, ${p.name}!`);
      pick(p);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  const list = role === "household" ? households : collectors;

  return (
    <div className="picker">
      <aside className="picker-aside">
        <div className="picker-kicker"><span aria-hidden="true">↻</span> Loop Local</div>
        <div className="picker-aside-copy">
          <h1>Good things deserve another go-round.</h1>
          <p>A neighbourly exchange for giving paper, plastic and more a useful next chapter.</p>
        </div>
        <div className="picker-circulation"><b aria-hidden="true">↻</b><span>Request it.<br />Collect it. Keep it moving.</span></div>
      </aside>
      <div className="picker-panel"><div className="picker-card">
        <h2>Join the neighbourhood loop</h2>
        <p className="muted">Choose how you’d like to participate today.</p>

        <div className="role-tabs" role="tablist" aria-label="Choose role">
          {["household", "collector"].map((r) => (
            <button key={r} role="tab" aria-selected={role === r}
              className={role === r ? "active" : ""} onClick={() => setRole(r)}>
              <span className="role-tab-icon" aria-hidden="true">{r === "household" ? "⌂" : "↗"}</span>
              {r === "household" ? "I’m a household" : "I’m a collector"}
            </button>
          ))}
        </div>

        <section className="trust-strip" aria-labelledby="trust-title">
          <div><span className="picker-section-label" id="trust-title">How the loop stays trustworthy</span><p>Each hand-off leaves a clear, accountable trail.</p></div>
          <ol>
            <li><b>1</b><span><strong>Request</strong>Post an estimate and area.</span></li>
            <li><b>2</b><span><strong>Eligible</strong>Only matching collectors see it.</span></li>
            <li><b>3</b><span><strong>Protected</strong>One collector can secure it.</span></li>
            <li><b>4</b><span><strong>Measured</strong>Actual kg is recorded.</span></li>
          </ol>
        </section>

        <p className="picker-section-label">Continue as an existing {role}</p>
        {list.length === 0 && <p className="muted">No {role} profiles yet — create one below.</p>}
        <ul className="profile-list">
          {list.map((p) => (
            <li key={p.id}>
              <button className="profile-btn" onClick={() => pick(p)} disabled={busy}>
                <strong>{p.name}</strong>
                <span className="muted">
                  {role === "household"
                    ? p.area
                    : `${p.accepted_materials.join(", ")} · ${p.service_areas.join(", ")}${p.active ? "" : " (inactive)"}`}
                </span>
              </button>
            </li>
          ))}
        </ul>

        {creating ? (
          <form className="create-form" onSubmit={create}>
            <h2>Create a new {role} profile</h2>
            <label>Name
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </label>
            <label>Phone
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} required />
            </label>
            {role === "household" ? (
              <label>Area
                <input list="areas" value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })} required />
                <datalist id="areas">{BENGALURU_AREAS.map((a) => <option key={a} value={a} />)}</datalist>
              </label>
            ) : (
              <>
                <fieldset>
                  <legend>Accepted materials</legend>
                  <div className="chip-row">
                    {MATERIALS.map((m) => (
                      <button type="button" key={m}
                        className={`chip ${form.materials.includes(m) ? "chip-on" : ""}`}
                        onClick={() => toggleMaterial(m)}>{m}</button>
                    ))}
                  </div>
                </fieldset>
                <label>Service areas (comma-separated)
                  <input value={form.serviceAreas}
                    onChange={(e) => setForm({ ...form, serviceAreas: e.target.value })}
                    placeholder="Koramangala, HSR Layout" />
                </label>
                <label>Max capacity kg (optional)
                  <input type="number" min="1" max="1000" value={form.capacity}
                    onChange={(e) => setForm({ ...form, capacity: e.target.value })} />
                </label>
              </>
            )}
            <div className="row">
              <button type="submit" className="primary" disabled={busy}>Create & continue</button>
              <button type="button" onClick={() => setCreating(false)}>Back</button>
            </div>
          </form>
        ) : (
          <button className="link" onClick={() => setCreating(true)}>+ Create a new {role} profile</button>
        )}
      </div></div>
    </div>
  );
}
