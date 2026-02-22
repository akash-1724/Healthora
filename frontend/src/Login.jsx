import React from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "./api";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const data = await api.login(username, password);
      localStorage.setItem("token", data.token);
      localStorage.setItem("username", data.username);
      localStorage.setItem("role", data.role);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        fontFamily: "Arial",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #dbeafe, #f0fdfa)",
      }}
    >
      <div style={{ width: 360, background: "white", padding: 24, borderRadius: 12, boxShadow: "0 10px 25px rgba(0,0,0,0.08)" }}>
        <h2 style={{ marginTop: 0, color: "#1e3a8a" }}>HEALTHORA Login</h2>
        <p style={{ marginTop: 0, color: "#4b5563", fontSize: 14 }}>Welcome back. Please sign in to continue.</p>
        <form onSubmit={handleSubmit}>
        <input
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={{ width: "100%", marginBottom: 10, padding: 10, borderRadius: 8, border: "1px solid #d1d5db" }}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ width: "100%", marginBottom: 10, padding: 10, borderRadius: 8, border: "1px solid #d1d5db" }}
        />
        <button type="submit" style={{ padding: "10px 14px", width: "100%", background: "#2563eb", color: "white", border: "none", borderRadius: 8, cursor: "pointer" }}>
          Login
        </button>
      </form>
        {error ? <p style={{ color: "#dc2626" }}>{error}</p> : null}
        <p style={{ marginBottom: 0, color: "#6b7280", fontSize: 13 }}>Default user: admin / admin123</p>
      </div>
    </div>
  );
}
