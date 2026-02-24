import React from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "./api";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api.login(username, password);
      const storage = rememberMe ? localStorage : sessionStorage;
      storage.setItem("token", data.access_token);
      storage.setItem("username", username);
      storage.setItem("role", data.role);
      storage.setItem("displayName", data.display_name);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-root">
      <div className="login-card">
        <h2 style={{ marginTop: 0 }}>HEALTHORA Login</h2>
        <p>Welcome back. Please sign in to continue.</p>
        <form onSubmit={handleSubmit}>
          <input className="input" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          <input className="input" type={showPassword ? "text" : "password"} placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <div className="actions-cell" style={{ marginBottom: 10 }}>
            <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} /> Remember me
            </label>
            <button type="button" className="secondary-btn compact" onClick={() => setShowPassword((prev) => !prev)}>
              {showPassword ? "Hide" : "Show"} Password
            </button>
          </div>
          <button type="submit" className="primary-btn" style={{ width: "100%" }} disabled={loading || !username || !password}>
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>
        {error ? <p className="error">{error}</p> : null}
        <p style={{ marginBottom: 0, fontSize: 13 }}>
          Seed users: sysadmin/admin, cmo1/cmo, pm1/manager, senior1/senior, staff1/staff, clerk1/clerk
        </p>
      </div>
    </div>
  );
}
