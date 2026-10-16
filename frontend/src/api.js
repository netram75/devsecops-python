// All calls are relative: nginx (compose) or the Ingress (k8s) routes /api to the backend.
export class ApiError extends Error {
  constructor(status, message, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function describe(detail, fallback) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => `${d.loc?.at(-1) ?? "field"}: ${d.msg.replace(/^Value error, /, "")}`).join(" · ");
  }
  return fallback;
}

async function request(path, { method = "GET", body } = {}) {
  let res;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Cannot reach the GearLoop API. Is the backend running?");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, describe(data.detail, res.statusText), data.code);
  return data;
}

const qs = (params) => {
  const s = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null));
  return s.toString() ? `?${s}` : "";
};

export const api = {
  info: () => request("/info"),
  stats: () => request("/stats"),
  activity: (limit = 12) => request(`/activity?limit=${limit}`),
  assets: (params = {}) => request(`/assets${qs(params)}`),
  createAsset: (body) => request("/assets", { method: "POST", body }),
  updateAsset: (id, body) => request(`/assets/${id}`, { method: "PUT", body }),
  deleteAsset: (id) => request(`/assets/${id}`, { method: "DELETE" }),
  assetLoans: (id) => request(`/assets/${id}/loans`),
  loans: (params = {}) => request(`/loans${qs(params)}`),
  createLoan: (body) => request("/loans", { method: "POST", body }),
  updateLoan: (id, body) => request(`/loans/${id}`, { method: "PUT", body }),
  deleteLoan: (id) => request(`/loans/${id}`, { method: "DELETE" }),
  transition: (id, action) => request(`/loans/${id}/${action}`, { method: "POST" }),
};
