// Thin fetch wrapper around the backend REST API with consistent error handling
// plus a small in-memory GET cache with ETag revalidation.
// In local development Vite proxies this path to FastAPI. This avoids a brittle
// CORS dependency on whichever port Vite selected. Deployments can still supply
// the API origin explicitly with VITE_API_URL.
const BASE = import.meta.env.VITE_API_URL || "/api";

// GET cache: url -> { etag, data }. Mutations clear the whole cache (simplest
// correct policy for this small prototype).
const cache = new Map();

async function request(path, options = {}) {
  const cacheable = (options.method || "GET") === "GET";
  const entry = cacheable ? cache.get(path) : null;

  const headers = { "Content-Type": "application/json", ...options.headers };
  if (entry?.etag) headers["If-None-Match"] = entry.etag;

  let res;
  try {
    res = await fetch(`${BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error(
      "Couldn’t reach the recycling service. Start the backend on port 8000 and try again."
    );
  }

  // 304 Not Modified: reuse the cached payload — no download, no state churn.
  if (res.status === 304 && entry) {
    return entry.data;
  }

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
    const error = new Error(msg);
    error.status = res.status;
    throw error;
  }

  if (cacheable) {
    cache.set(path, { etag: res.headers.get("ETag"), data: body });
  }
  return body;
}

/** Clear the whole GET cache — simplest correct policy after any mutation. */
export function clearCache() {
  cache.clear();
}

/** Run a mutation, then clear the GET cache so the next poll sees fresh data. */
async function mutate(fn) {
  const result = await fn();
  clearCache();
  return result;
}

export const api = {
  // profiles
  households: () => request("/households"),
  collectors: () => request("/collectors"),
  createHousehold: (data) =>
    mutate(() => request("/households", { method: "POST", body: JSON.stringify(data) })),
  createCollector: (data) =>
    mutate(() => request("/collectors", { method: "POST", body: JSON.stringify(data) })),
  getCollector: (id) => request(`/collectors/${id}`),
  updateCollector: (id, data) =>
    mutate(() => request(`/collectors/${id}`, { method: "PUT", body: JSON.stringify(data) })),

  // household
  createRequest: (data) =>
    mutate(() => request("/requests", { method: "POST", body: JSON.stringify(data) })),
  householdRequests: (id) => request(`/households/${id}/requests`),
  getRequest: (id) => request(`/requests/${id}`),
  cancelRequest: (id, household_id) =>
    mutate(() =>
      request(`/requests/${id}/cancel`, { method: "POST", body: JSON.stringify({ household_id }) })
    ),

  // collector
  availableRequests: (id) => request(`/collectors/${id}/available-requests`),
  claim: (id, collector_id) =>
    mutate(() =>
      request(`/requests/${id}/claim`, { method: "POST", body: JSON.stringify({ collector_id }) })
    ),
  collectorRequests: (id, status) =>
    request(`/collectors/${id}/requests${status ? `?status=${status}` : ""}`),
  complete: (id, collector_id, actual_weight_kg, notes) =>
    mutate(() =>
      request(`/requests/${id}/complete`, {
        method: "POST",
        body: JSON.stringify({ collector_id, actual_weight_kg, notes: notes || null }),
      })
    ),
  fail: (id, collector_id, reason) =>
    mutate(() =>
      request(`/requests/${id}/fail`, { method: "POST", body: JSON.stringify({ collector_id, reason }) })
    ),
  collectorCancel: (id, collector_id, reason) =>
    mutate(() =>
      request(`/requests/${id}/collector-cancel`, {
        method: "POST",
        body: JSON.stringify({ collector_id, reason }),
      })
    ),

  // stats
  stats: () => request("/stats/summary"),
};

export const MATERIALS = ["Paper", "Plastic", "Metal", "Glass", "E-waste", "Cardboard", "Mixed"];
