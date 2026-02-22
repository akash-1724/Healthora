const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeader() {
  const token = localStorage.getItem("token");
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
  getUsers: () => request("/api/users"),
  getRoles: () => request("/api/users/roles"),
  createUser: (payload) => request("/api/users", { method: "POST", body: JSON.stringify(payload) }),
  updateUser: (userId, payload) => request(`/api/users/${userId}`, { method: "PUT", body: JSON.stringify(payload) }),
  getInventory: () => request("/api/inventory"),
};
