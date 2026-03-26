import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "./api";
import "./styles.css";

export default function Login() {
  const [mode, setMode] = useState("login");
  const [setupRequired, setSetupRequired] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [bootstrapKey, setBootstrapKey] = useState("1");
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      try {
        const status = await api.setupStatus();
        const needsSetup = Boolean(status.requires_sysadmin_setup);
        setSetupRequired(needsSetup);
        if (needsSetup) {
          setMode("register");
        }
      } catch {
        setSetupRequired(false);
      }
    })();
  }, []);

  function persistAuth(data) {
    const store = rememberMe ? localStorage : sessionStorage;
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("username");
    sessionStorage.removeItem("role");
    store.setItem("token", data.access_token);
    store.setItem("username", username);
    store.setItem("role", data.role);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = mode === "register"
        ? await api.registerSysadmin({
          username,
          password,
          full_name: fullName || null,
          email: email || null,
          phone: phone || null,
          bootstrap_key: bootstrapKey || null,
        })
        : await api.login(username, password);
      persistAuth(data);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const hints = [
    { user: "a.sharma", pass: "$123q", role: "System Admin" },
    { user: "j.doe", pass: "$123q", role: "Chief Medical Officer" },
    { user: "pharm.chief", pass: "$123q", role: "Pharmacy Manager" },
    { user: "s.patel", pass: "$123q", role: "Senior Pharmacist" },
    { user: "r.jones", pass: "$123q", role: "Staff Pharmacist" },
    { user: "inv.clerk1", pass: "$123q", role: "Clerk" },
    { user: "doctor1", pass: "doctor123", role: "Doctor" },
  ];

  return (
    <div className="login-root">
      <div className="login-card">
        <div className="login-logo">
          <div className="login-logo-icon">💊</div>
          <h1>HEALTHORA</h1>
          <p>Smart Pharmacy Management System</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="inline-controls" style={{ marginBottom: 8 }}>
            <button
              type="button"
              className={`secondary-btn compact ${mode === "login" ? "active-btn" : ""}`}
              onClick={() => setMode("login")}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`secondary-btn compact ${mode === "register" ? "active-btn" : ""}`}
              onClick={() => setMode("register")}
            >
              Register Sysadmin
            </button>
          </div>

          <div className="login-field">
            <label>Username</label>
            <input className="input" placeholder="Enter username..." value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username" />
          </div>

          {mode === "register" && (
            <>
              <div className="login-field">
                <label>Full Name</label>
                <input className="input" placeholder="Enter full name" value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" />
              </div>
              <div className="login-field">
                <label>Email</label>
                <input className="input" type="email" placeholder="Enter email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
              </div>
              <div className="login-field">
                <label>Phone</label>
                <input className="input" placeholder="Enter phone" value={phone} onChange={(e) => setPhone(e.target.value)} autoComplete="tel" />
              </div>
              <div className="login-field">
                <label>Hospital Key</label>
                <input className="input" value={bootstrapKey} onChange={(e) => setBootstrapKey(e.target.value)} placeholder="Optional bootstrap key" />
              </div>
            </>
          )}

          <div className="login-field">
            <label>Password</label>
            <div style={{ position: "relative" }}>
              <input
                className="input"
                type={showPassword ? "text" : "password"}
                placeholder="Enter password..."
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                style={{ paddingRight: 48 }}
              />
              <button
                type="button"
                onClick={() => setShowPassword((p) => !p)}
                style={{
                  position: "absolute", right: 10, top: "50%",
                  transform: "translateY(-50%)", background: "none",
                  border: "none", cursor: "pointer", fontSize: 17,
                  color: "#9ca3af", padding: "2px 4px",
                }}
                aria-label="Toggle password visibility"
              >
                {showPassword ? "🙈" : "👁️"}
              </button>
            </div>
          </div>

          {error && <div className="error-msg">⚠️ {error}</div>}

          <button type="submit" className="primary-btn login-submit" disabled={loading || !username || !password}>
            {loading ? "Submitting..." : (mode === "register" ? "→ Create Sysadmin" : "→ Sign In")}
          </button>

          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>
            <input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} />
            Remember me on this device
          </label>
        </form>

        {mode === "login" && (
          <div className="login-hint">
            <div style={{ fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", fontSize: 11, marginBottom: 10, color: "#374151" }}>
              Demo Credentials (click to autofill)
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 16px" }}>
              {hints.map((h) => (
                <div
                  key={h.user}
                  onClick={() => { setUsername(h.user); setPassword(h.pass); }}
                  style={{
                    cursor: "pointer",
                    background: "#fff",
                    border: "2px solid #d1d5db",
                    padding: "6px 10px",
                    boxShadow: "2px 2px 0 #d1d5db",
                    transition: "all 0.12s",
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.transform = "translate(-2px,-2px)"; e.currentTarget.style.boxShadow = "4px 4px 0 #0d0d0d"; e.currentTarget.style.borderColor = "#0d0d0d"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = "2px 2px 0 #d1d5db"; e.currentTarget.style.borderColor = "#d1d5db"; }}
                  title={`Login as ${h.role}`}
                >
                  <div style={{ fontWeight: 700, fontSize: 13, color: "#0d0d0d" }}>{h.user}<span style={{ color: "#9ca3af", fontWeight: 400 }}> / {h.pass}</span></div>
                  <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>{h.role}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
