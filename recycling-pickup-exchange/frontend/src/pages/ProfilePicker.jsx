import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, MATERIALS } from "../api";
import { useProfile } from "../profileContext";
import { useToast } from "../toastContext";
import "./picker.css";

// "Continue as…" screen shown on first load (and via Switch profile).
// Choose a role, pick a seeded profile, or create a new one.
const BENGALURU_AREAS = ["Koramangala", "Indiranagar", "Whitefield", "Jayangar", "HSR Layout", "BTM Layout"];

// Per-role copy for the hero aside + trust strip, driven by the same CSS design.
const ROLE_META = {
  household: {
    tab: "I'm a Household",
    icon: "🏠",
    kicker: "For residents",
    copy: "Post what you need collected, and local collectors in your area will claim it. Track every pickup from request to verified weight.",
    empty: "No household profiles yet — create one below.",
    trustLabel: "How it works",
    trustNote: "One collector per request, guaranteed.",
    trust: [
      ["1", "Post", "List your recyclables"],
      ["2", "Matched", "A collector claims it"],
      ["3", "Picked up", "Collected at your door"],
      ["4", "Verified", "Actual kg recorded"],
    ],
  },
  collector: {
    tab: "I'm a Collector",
    icon: "🚛",
    kicker: "For collectors",
    copy: "See only the requests that fit your accepted materials and service areas. Claim instantly — no double-booking, ever.",
    empty: "No collector profiles yet — create one below.",
    trustLabel: "Your workflow",
    trustNote: "First claim wins, others are locked out.",
    trust: [
      ["1", "Set up", "Materials & areas"],
      ["2", "Claim", "Atomic, no conflicts"],
      ["3", "Collect", "Pick up & confirm"],
      ["4", "Log", "Actual weight in"],
    ],
  },
};

export default function ProfilePicker() {
  const { setProfile } = useProfile();
  const toast = useToast();
  const navigate = useNavigate();
  const [role, setRole] = useState("household");
  const [households, setHouseholds] = useState([]);
  const [collectors, setCollectors] = useState([]);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  // create-form state
  const [form, setForm] = useState({ name: "", phone: "", area: "", materials: [], serviceAreas: "", capacity: "" });

  useEffect(() => {
    Promise.all([api.households(), api.collectors()])
      .then(([h, c]) => {
        setHouseholds(h);
        setCollectors(c);
      })
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pick = (p) => {
    setProfile({ role, ...p });
    navigate("/dashboard");
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

  const meta = ROLE_META[role];
  const list = role === "household" ? households : collectors;

  return (
    <div className="picker">
      {/* Hero aside */}
      <aside className="picker-aside">
        <p className="picker-kicker">
          <span aria-hidden="true">♻️</span> {meta.kicker}
        </p>
        <div className="picker-aside-copy">
          <h1>Recyclables,<br />routed right.</h1>
          <p>{meta.copy}</p>
        </div>
        <p className="picker-circulation">
          <b aria-hidden="true">🌿</b>
          <span><strong>Team Nexora</strong><br />Tech Fusion 2026 · EcoRoute prototype</span>
        </p>
      </aside>

      {/* Selection panel */}
      <main className="picker-panel">
        <div className="picker-card">
          <div className="trust-strip">
            <div>
              <p className="picker-section-label">{meta.trustLabel}</p>
              <p>{meta.trustNote}</p>
            </div>
            <ol>
              {meta.trust.map(([n, title, sub]) => (
                <li key={n}><b>{n}</b><strong>{title}</strong><span>{sub}</span></li>
              ))}
            </ol>
          </div>

          <div className="role-tabs" role="tablist" aria-label="Choose role">
            {Object.entries(ROLE_META).map(([r, m]) => (
              <button key={r} role="tab" aria-selected={role === r}
                className={role === r ? "active" : ""} onClick={() => setRole(r)}>
                <span className="role-tab-icon" aria-hidden="true">{m.icon}</span>
                {m.tab}
              </button>
            ))}
          </div>

          <h2>Continue as an existing {role}</h2>
          {loading ? (
            <p className="muted">Loading profiles…</p>
          ) : list.length === 0 ? (
            <p className="muted">{meta.empty}</p>
          ) : (
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
          )}

          {creating ? (
            <form className="create-form" onSubmit={create}>
              <h2>Create a new {role} profile</h2>
              <div className="create-grid">
                <label>Name
                  <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                </label>
                <label>Phone
                  <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} required />
                </label>
              </div>
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
                  <div className="create-grid">
                    <label>Service areas (comma-separated)
                      <input value={form.serviceAreas}
                        onChange={(e) => setForm({ ...form, serviceAreas: e.target.value })}
                        placeholder="Koramangala, HSR Layout" />
                    </label>
                    <label>Max capacity kg (optional)
                      <input type="number" min="1" max="1000" value={form.capacity}
                        onChange={(e) => setForm({ ...form, capacity: e.target.value })} />
                    </label>
                  </div>
                </>
              )}
              <div className="row">
                <button type="submit" className="primary" disabled={busy}>
                  {busy ? "Creating…" : "Create & continue"}
                </button>
                <button type="button" onClick={() => setCreating(false)}>Back</button>
              </div>
            </form>
          ) : (
            <button className="link" onClick={() => setCreating(true)}>+ Create a new {role} profile</button>
          )}
        </div>
      </main>
    </div>
  );
}
