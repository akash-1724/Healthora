const API_BASE = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:8000`;

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
  if (!res.ok) throw new Error(normalizeApiError(data));
  return data;
}

async function requestForm(path, formData) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { ...authHeader() },
    body: formData,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(normalizeApiError(data));
  return data;
}

async function requestBlob(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeader(), ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(normalizeApiError(data));
  }
  return res.blob();
}

function normalizeApiError(data) {
  const detail = data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === "string") return first;
    if (first && typeof first === "object") {
      return first.msg || first.message || JSON.stringify(first);
    }
  }
  if (detail && typeof detail === "object") {
    return detail.message || JSON.stringify(detail);
  }
  return "Request failed";
}

export const api = {
  // ── Auth ──────────────────────────────────────────────────────────────
  login: (username, password) => request("/api/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  setupStatus: () => request("/api/setup-status"),
  registerSysadmin: (payload) => request("/api/register-sysadmin", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request("/api/me"),

  // ── Dashboard ─────────────────────────────────────────────────────────
  dashboardSummary: () => request("/api/dashboard-summary"),
  dashboardExpiry: () => request("/api/dashboard-expiry"),
  dashboardAccess: () => request("/api/dashboard-access"),

  // ── Notifications (DB-backed) ─────────────────────────────────────────
  getNotifications: () => request("/api/notifications"),
  markNotificationRead: (id) => request(`/api/notifications/${id}/read`, { method: "PATCH" }),
  markAllNotificationsRead: () => request("/api/notifications/read-all", { method: "PATCH" }),
  clearNotifications: () => request("/api/notifications/clear", { method: "DELETE" }),

  // ── Users ─────────────────────────────────────────────────────────────
  getUsers: () => request("/api/users"),
  createUser: (payload) => request("/api/users", { method: "POST", body: JSON.stringify(payload) }),
  updateUser: (userId, payload) => request(`/api/users/${userId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deactivateUser: (userId) => request(`/api/users/${userId}/deactivate`, { method: "PATCH" }),
  resetUserPassword: (userId, password) => request(`/api/users/${userId}/reset-password`, { method: "PATCH", body: JSON.stringify({ password }) }),
  deleteUser: (userId) => request(`/api/users/${userId}`, { method: "DELETE" }),
  getRoles: () => request("/api/roles"),
  getDepartments: () => request("/api/departments"),

  // ── Patients ──────────────────────────────────────────────────────────
  getPatients: () => request("/api/patients"),
  createPatient: (payload) => request("/api/patients", { method: "POST", body: JSON.stringify(payload) }),
  updatePatient: (patientId, payload) => request(`/api/patients/${patientId}`, { method: "PUT", body: JSON.stringify(payload) }),
  archivePatient: (patientId) => request(`/api/patients/${patientId}/archive`, { method: "PATCH" }),

  // ── Drugs ─────────────────────────────────────────────────────────────
  getDrugs: () => request("/api/drugs"),
  createDrug: (payload) => request("/api/drugs", { method: "POST", body: JSON.stringify(payload) }),
  updateDrug: (drugId, payload) => request(`/api/drugs/${drugId}`, { method: "PUT", body: JSON.stringify(payload) }),
  disableDrug: (drugId) => request(`/api/drugs/${drugId}/disable`, { method: "PATCH" }),

  // ── Inventory / Batches ───────────────────────────────────────────────
  getInventory: (params = "") => request(`/api/inventory${params}`),
  updateInventory: (batchId, payload) => request(`/api/inventory/${batchId}`, { method: "PUT", body: JSON.stringify(payload) }),
  createBatch: (payload) => request("/api/drug-batches", { method: "POST", body: JSON.stringify(payload) }),
  bulkUploadBatches: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return requestForm("/api/drug-batches/bulk-upload", formData);
  },
  markBatchExpired: (batchId) => request(`/api/drug-batches/${batchId}/mark-expired`, { method: "PATCH" }),

  // ── Suppliers ─────────────────────────────────────────────────────────
  getSuppliers: () => request("/api/suppliers"),
  createSupplier: (payload) => request("/api/suppliers", { method: "POST", body: JSON.stringify(payload) }),
  updateSupplier: (id, payload) => request(`/api/suppliers/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteSupplier: (id) => request(`/api/suppliers/${id}`, { method: "DELETE" }),

  // ── Purchase Orders ───────────────────────────────────────────────────
  getPurchaseOrders: () => request("/api/purchase-orders"),
  createPurchaseOrder: (payload) => request("/api/purchase-orders", { method: "POST", body: JSON.stringify(payload) }),
  updatePOStatus: (poId, status) => request(`/api/purchase-orders/${poId}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),

  // ── Prescriptions ─────────────────────────────────────────────────────
  getPrescriptions: (patientId) => request(`/api/prescriptions${patientId ? `?patient_id=${patientId}` : ""}`),
  createPrescription: (payload) => request("/api/prescriptions", { method: "POST", body: JSON.stringify(payload) }),
  cancelPrescription: (id) => request(`/api/prescriptions/${id}/cancel`, { method: "PATCH" }),

  // ── Dispensing ────────────────────────────────────────────────────────
  getDispensingRecords: (patientId) => request(`/api/dispensing${patientId ? `?patient_id=${patientId}` : ""}`),
  dispense: (payload) => request("/api/dispensing", { method: "POST", body: JSON.stringify(payload) }),
  dispatchPrescription: (prescriptionId) => request(`/api/dispensing/dispatch/${prescriptionId}`, { method: "POST" }),

  // ── Audit Logs ────────────────────────────────────────────────────────
  getAuditLogs: (action) => request(`/api/audit-logs${action ? `?action=${action}` : ""}`),

  // ── AI Report ─────────────────────────────────────────────────────────
  aiReportStatus: () => request("/api/ai-report"),
  aiReportQuery: (question) => request("/api/ai-report/query", { method: "POST", body: JSON.stringify({ question }) }),
  aiGenerateReport: (question) => request("/api/ai-report/generate-report", { method: "POST", body: JSON.stringify({ question }) }),
  aiReportPreview: (reportId) => request(`/api/ai-report/${reportId}/preview`),
  aiDownloadReport: (reportId, format) => requestBlob(`/api/ai-report/${reportId}/download`, { method: "POST", body: JSON.stringify({ format }) }),
  aiReportRagStats: () => request("/api/ai-report/rag/stats"),
};
