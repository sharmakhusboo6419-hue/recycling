// Thin fetch wrapper around the backend REST API with consistent error handling.
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* no body */
  }
  if (!res.ok) {
    const detail =
      body?.detail ||
      (typeof body === "string" ? body : null) ||
      `Request failed (${res.status})`;
    // Pydantic 422 returns a list of validation errors — summarise it.
    const msg =
      Array.isArray(detail)
        ? detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ")
        : String(detail);
    throw new Error(msg);
  }
  return body;
}

export const api = {
  // profiles
  households: () => request("/households"),
  collectors: () => request("/collectors"),
  createHousehold: (data) => request("/households", { method: "POST", body: JSON.stringify(data) }),
  createCollector: (data) => request("/collectors", { method: "POST", body: JSON.stringify(data) }),
  getCollector: (id) => request(`/collectors/${id}`),
  updateCollector: (id, data) => request(`/collectors/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  // household
  createRequest: (data) => request("/requests", { method: "POST", body: JSON.stringify(data) }),
  householdRequests: (id) => request(`/households/${id}/requests`),
  getRequest: (id) => request(`/requests/${id}`),
  cancelRequest: (id, household_id) =>
    request(`/requests/${id}/cancel`, { method: "POST", body: JSON.stringify({ household_id }) }),

  // collector
  availableRequests: (id) => request(`/collectors/${id}/available-requests`),
  claim: (id, collector_id) =>
    request(`/requests/${id}/claim`, { method: "POST", body: JSON.stringify({ collector_id }) }),
  collectorRequests: (id, status) =>
    request(`/collectors/${id}/requests${status ? `?status=${status}` : ""}`),
  complete: (id, collector_id, actual_weight_kg, notes) =>
    request(`/requests/${id}/complete`, {
      method: "POST",
      body: JSON.stringify({ collector_id, actual_weight_kg, notes: notes || null }),
    }),
  fail: (id, collector_id, reason) =>
    request(`/requests/${id}/fail`, { method: "POST", body: JSON.stringify({ collector_id, reason }) }),
  collectorCancel: (id, collector_id, reason) =>
    request(`/requests/${id}/collector-cancel`, { method: "POST", body: JSON.stringify({ collector_id, reason }) }),

  // stats
  stats: () => request("/stats/summary"),
};

export const MATERIALS = ["Paper", "Plastic", "Metal", "Glass", "E-waste", "Cardboard", "Mixed"];
