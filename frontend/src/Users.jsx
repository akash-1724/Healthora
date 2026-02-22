import React from "react";
import { useEffect, useState } from "react";

import { api } from "./api";

export default function Users() {
  const [users, setUsers] = useState([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [roleId, setRoleId] = useState(undefined);
  // default role names to show in the UI immediately
  const DEFAULT_ROLES = [
    "System Admin",
    "Chief Medical Officer",
    "Pharmacy Manager",
    "Senior Pharmacist",
    "Staff Pharmacist",
    "Inventory Clerk",
  ];
  const [roles, setRoles] = useState(DEFAULT_ROLES.map((n) => ({ id: undefined, name: n })));
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [editingUserId, setEditingUserId] = useState(null);
  const [editingRoleId, setEditingRoleId] = useState(null);

  async function loadUsers() {
    try {
      const data = await api.getUsers();
      setUsers(data);
      setError("");
      try {
        const r = await api.getRoles();
        setRoles(r);
        if (r && r.length > 0) setRoleId(r[0].id);
      } catch (e) {
        // ignore role load errors here
      }
    } catch (err) {
      setError("Could not load users from server.");
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function addUser(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      // Ensure we submit a numeric role_id. If the selected role value
      // is a name (string), resolve it to an id by fetching roles.
      let submittedRoleId = Number(roleId);
      if (Number.isNaN(submittedRoleId)) {
        try {
          const remoteRoles = await api.getRoles();
          const match = remoteRoles.find((r) => r.name === roleId);
          submittedRoleId = match ? match.id : 2;
        } catch (e) {
          // fallback to first available role
          submittedRoleId = 3;
        }
      }

      await api.createUser({ username, password, role_id: Number(submittedRoleId), is_active: true });
      setSuccess(`User "${username}" created successfully.`);
      setUsername("");
      setPassword("");
      setRoleId(undefined);
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to create user.");
    } finally {
      setLoading(false);
    }
  }

  async function updateUserRole(userId, newRoleId) {
    try {
      await api.updateUser(userId, { role_id: newRoleId });
      setSuccess("User role updated successfully.");
      setEditingUserId(null);
      setEditingRoleId(null);
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to update user role.");
    }
  }

  return (
    <div style={{ fontFamily: "Arial" }}>
      <h2 style={{ marginTop: 0 }}>Users</h2>
      <p style={{ color: "#475569" }}>Manage users for Healthora.</p>

      <form onSubmit={addUser} style={{ marginTop: 12, maxWidth: 360, background: "white", border: "1px solid #dbe2ea", padding: 14, borderRadius: 12 }}>
        <h3 style={{ marginTop: 0 }}>Add User</h3>
        <input
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={{ width: "100%", marginBottom: 8, padding: 10, borderRadius: 8, border: "1px solid #d1d5db", boxSizing: "border-box" }}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ width: "100%", marginBottom: 8, padding: 10, borderRadius: 8, border: "1px solid #d1d5db", boxSizing: "border-box" }}
          required
        />
        <select
          value={roleId}
          onChange={(e) => setRoleId(e.target.value)}
          style={{ width: "100%", marginBottom: 8, padding: 10, borderRadius: 8, border: "1px solid #d1d5db", boxSizing: "border-box" }}
        >
          {roles.map((r, idx) => (
            <option key={r.id ?? `d${idx}`} value={r.id ?? r.name}>
              {r.name}{r.id ? ` (ID: ${r.id})` : ""}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={loading}
          style={{ padding: "9px 12px", border: "none", borderRadius: 8, background: loading ? "#93c5fd" : "#2563eb", color: "white", cursor: loading ? "not-allowed" : "pointer", width: "100%" }}
        >
          {loading ? "Adding..." : "Add User"}
        </button>
      </form>

      {error ? <p style={{ color: "#dc2626", marginTop: 8 }}>{error}</p> : null}
      {success ? <p style={{ color: "#16a34a", marginTop: 8 }}>{success}</p> : null}

      <div style={{ marginTop: 14, background: "white", border: "1px solid #dbe2ea", borderRadius: 12, padding: 14 }}>
        <h3 style={{ marginTop: 0 }}>Users List</h3>
        {users.length === 0 ? (
          <p style={{ color: "#94a3b8" }}>No users found.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead style={{ background: "#eff6ff" }}>
              <tr>
                <th style={{ textAlign: "left", padding: "8px 12px" }}>Username</th>
                <th style={{ textAlign: "left", padding: "8px 12px" }}>Role</th>
                <th style={{ textAlign: "left", padding: "8px 12px" }}>Active</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.user_id} style={{ borderTop: "1px solid #eef2f7" }}>
                  <td style={{ padding: "8px 12px" }}>{u.username}</td>
                  <td style={{ padding: "8px 12px" }}>
                    {editingUserId === u.user_id ? (
                      <div style={{ display: "flex", gap: 8 }}>
                        <select
                          value={editingRoleId || u.role_id}
                          onChange={(e) => setEditingRoleId(Number(e.target.value))}
                          style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid #d1d5db" }}
                        >
                          {roles.map((r) => (
                            <option key={r.id ?? `d${r.name}`} value={r.id}>
                              {r.name}
                            </option>
                          ))}
                        </select>
                        <button
                          onClick={() => updateUserRole(u.user_id, editingRoleId)}
                          style={{ padding: "4px 8px", background: "#16a34a", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingUserId(null)}
                          style={{ padding: "4px 8px", background: "#666", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <div style={{ cursor: "pointer", color: "#2563eb" }} onClick={() => { setEditingUserId(u.user_id); setEditingRoleId(u.role_id); }}>
                        {u.role || u.role_id} [Edit]
                      </div>
                    )}
                  </td>
                  <td style={{ padding: "8px 12px" }}>{u.is_active ? "✅" : "❌"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
