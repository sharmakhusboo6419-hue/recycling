import { useState } from "react";
import { api, MATERIALS } from "../api";
import { useToast } from "../toastContext";

// Household "new pickup request" form with inline client-side validation.
export default function RequestForm({ householdId, onCreated }) {
  const toast = useToast();
  const [form, setForm] = useState({ material_type: "Paper", estimated_weight_kg: "", area: "", address_note: "", preferred_time: "" });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);

  const validate = () => {
    const e = {};
    if (!form.material_type) e.material_type = "Choose a material.";
    const w = Number(form.estimated_weight_kg);
    if (!form.estimated_weight_kg || Number.isNaN(w) || w <= 0) e.estimated_weight_kg = "Weight must be a positive number.";
    else if (w > 1000) e.estimated_weight_kg = "Maximum is 1000 kg.";
    if (!form.area.trim()) e.area = "Area is required.";
    return e;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) return;
    setBusy(true);
    try {
      await api.createRequest({
        household_id: householdId,
        material_type: form.material_type,
        estimated_weight_kg: Number(form.estimated_weight_kg),
        area: form.area,
        address_note: form.address_note || null,
        preferred_time: form.preferred_time || null,
      });
      setForm({ material_type: "Paper", estimated_weight_kg: "", area: "", address_note: "", preferred_time: "" });
      onCreated?.();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="req-form" onSubmit={submit} noValidate>
      <label>Material
        <select value={form.material_type} onChange={(e) => setForm({ ...form, material_type: e.target.value })}>
          {MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        {errors.material_type && <span className="err">{errors.material_type}</span>}
      </label>
      <label>Estimated weight (kg)
        <input type="number" step="0.1" min="0.1" max="1000" value={form.estimated_weight_kg}
          onChange={(e) => setForm({ ...form, estimated_weight_kg: e.target.value })}
          aria-invalid={!!errors.estimated_weight_kg} />
        {errors.estimated_weight_kg && <span className="err">{errors.estimated_weight_kg}</span>}
      </label>
      <label>Area
        <input value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })}
          placeholder="e.g. Koramangala" aria-invalid={!!errors.area} />
        {errors.area && <span className="err">{errors.area}</span>}
      </label>
      <label>Address note (optional)
        <input value={form.address_note} onChange={(e) => setForm({ ...form, address_note: e.target.value })}
          placeholder="e.g. Gate 4, Green View Apartments" />
      </label>
      <label>Preferred time (optional)
        <select value={form.preferred_time} onChange={(e) => setForm({ ...form, preferred_time: e.target.value })}>
          <option value="">Any time</option>
          <option>Morning</option>
          <option>Afternoon</option>
          <option>Evening</option>
        </select>
      </label>
      <button className="primary" type="submit" disabled={busy}>
        {busy ? "Posting…" : "Post request"}
      </button>
    </form>
  );
}
