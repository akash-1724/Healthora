import React from "react";
import { useEffect, useState } from "react";

import { api } from "./api";

export default function Users() {
  const [users, setUsers] = useState([{ user_id: 1, username: "admin", role_id: 1 }]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [roleId, setRoleId] = useState(1);
  const [error, setError] = useState("");

  async function loadUsers() {
    try {
      const data = await api.getUsers();
      if (data.length > 0) setUsers(data);
      setError("");
    } catch (err) {
      setError("Showing local sample users. ");
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function addUser(e) {
    e.preventDefault();
    const next = {
      user_id: users.length + 1,
      username,
      role_id: Number(roleId),
      password,
    };
    setUsers([...users, next]);
    setUsername("");
    setPassword("");
    setRoleId(1);
  }

  return (
    <div style={{ fontFamily: "Arial" }}>
      <h2 style={{ marginTop: 0 }}>Users</h2>
      <p style={{ color: "#475569" }}>Manage users for Healthora. </p>

      <form onSubmit={addUser} style={{ marginTop: 12, maxWidth: 360, background: "white", border: "1px solid #dbe2ea", padding: 14, borderRadius: 12 }}>
        <h3 style={{ marginTop: 0 }}>Add User</h3>
        <input
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={{ width: "100%", marginBottom: 8, padding: 10, borderRadius: 8, border: "1px solid #d1d5db" }}
          required
        />
        <input
          type="text"
          placeholder="Password (plain text)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ width: "100%", marginBottom: 8, padding: 10, borderRadius: 8, border: "1px solid #d1d5db" }}
          required
        />
        <input
          type="number"
          placeholder="Role ID"
          value={roleId}
          onChange={(e) => setRoleId(e.target.value)}
          style={{ width: "100%", marginBottom: 8, padding: 10, borderRadius: 8, border: "1px solid #d1d5db" }}
        />
        <div style={{ display: "flex", gap: 8 }}>
          <button type="submit" style={{ padding: "9px 12px", border: "none", borderRadius: 8, background: "#2563eb", color: "white", cursor: "pointer" }}>
            Add User
          </button>
          <button type="button" style={{ padding: "9px 12px", border: "none", borderRadius: 8, background: "#0ea5e9", color: "white", cursor: "pointer" }}>
            Save
          </button>
        </div>
      </form>

      {error ? <p style={{ color: "#b45309" }}>{error}</p> : null}

      <div style={{ marginTop: 14, background: "white", border: "1px solid #dbe2ea", borderRadius: 12, padding: 14 }}>
        <h3 style={{ marginTop: 0 }}>Users List</h3>
        <ul>
          {users.map((u) => (
            <li key={u.user_id}>
              {u.username} (role: {u.role_id})
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
