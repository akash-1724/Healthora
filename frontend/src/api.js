const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeader() {
  const token = localStorage.getItem("token") || sessionStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeader(), ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

export const api = {
  login: (username, password) => request("/api/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: () => request("/api/me"),
  dashboardSummary: () => request("/api/dashboard-summary"),
  dashboardExpiry: () => request("/api/dashboard-expiry"),
  dashboardNotifications: () => request("/api/dashboard-notifications"),
  dashboardAccess: () => request("/api/dashboard-access"),
  getUsers: () => request("/api/users"),
  createUser: (payload) => request("/api/users", { method: "POST", body: JSON.stringify(payload) }),
  updateUser: (userId, payload) => request(`/api/users/${userId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deactivateUser: (userId) => request(`/api/users/${userId}/deactivate`, { method: "PATCH" }),
  resetUserPassword: (userId, password) => request(`/api/users/${userId}/reset-password`, { method: "PATCH", body: JSON.stringify({ password }) }),
  deleteUser: (userId) => request(`/api/users/${userId}`, { method: "DELETE" }),
  getRoles: () => request("/api/roles"),
  getDepartments: () => request("/api/departments"),
  getInventory: () => request("/api/inventory"),
  updateInventory: (batchId, payload) => request(`/api/inventory/${batchId}`, { method: "PUT", body: JSON.stringify(payload) }),
  getPatients: () => request("/api/patients"),
  createPatient: (payload) => request("/api/patients", { method: "POST", body: JSON.stringify(payload) }),
  updatePatient: (patientId, payload) => request(`/api/patients/${patientId}`, { method: "PUT", body: JSON.stringify(payload) }),
  archivePatient: (patientId) => request(`/api/patients/${patientId}/archive`, { method: "PATCH" }),
  getDrugs: () => request("/api/drugs"),
  createDrug: (payload) => request("/api/drugs", { method: "POST", body: JSON.stringify(payload) }),
  updateDrug: (drugId, payload) => request(`/api/drugs/${drugId}`, { method: "PUT", body: JSON.stringify(payload) }),
  disableDrug: (drugId) => request(`/api/drugs/${drugId}/disable`, { method: "PATCH" }),
  createBatch: (payload) => request("/api/drug-batches", { method: "POST", body: JSON.stringify(payload) }),
  markBatchExpired: (batchId) => request(`/api/drug-batches/${batchId}/mark-expired`, { method: "PATCH" }),
  aiReport: () => request("/api/ai-report"),
};
