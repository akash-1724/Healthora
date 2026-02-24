import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "./api";

export default function Landing() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await api.login(username, password);
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("username", username);
      localStorage.setItem("role", data.role);
      localStorage.setItem("displayName", data.display_name);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="hp-root">
      <header className="hp-nav-wrap">
        <div className="hp-container hp-nav">
          <a href="#home" className="hp-logo">
            <span className="hp-logo-box">H</span>
            <span>HEALTH<span className="hp-primary">ORA</span></span>
          </a>
          <nav className="hp-links">
            <a href="#features">Features</a>
            <a href="#about">About</a>
            <a href="#team">Team</a>
            <a href="#login" className="hp-link-btn">Sign In</a>
          </nav>
        </div>
      </header>

      <section className="hp-hero" id="home">
        <div className="hp-container hp-hero-grid">
          <div>
            <div className="hp-tag hp-tag-orange">Work In Progress</div>
            <h1 className="hp-hero-title">HEALTH<span className="hp-primary">ORA</span></h1>
            <p className="hp-subtitle">
              A Predictive Intelligence Core for <span className="hp-secondary">Modern Hospital Pharmacies</span>
            </p>
            <p className="hp-desc">
              HEALTHORA adds AI-powered batch analytics, consumption forecasting, and intelligent reorder planning to help teams move from reactive stock handling to predictive operations.
            </p>
            <div className="hp-actions">
              <a href="#login" className="hp-btn hp-btn-primary">Get Started</a>
              <a href="#features" className="hp-btn">Explore Features</a>
            </div>
          </div>
          <div className="hp-hero-cards">
            <div className="hp-float-card">🔐</div>
            <div className="hp-float-card hp-float-card-b">💊</div>
            <div className="hp-float-card hp-float-card-c">📈</div>
            <div className="hp-core">🧠</div>
          </div>
        </div>
      </section>

      <section className="hp-section" id="features">
        <div className="hp-container">
          <div className="hp-header">
            <div className="hp-tag hp-tag-orange">What It Does</div>
            <h2>System <span className="hp-primary">Capabilities</span></h2>
            <p>Core modules built for pharmacy operations, inventory safety, and clinical visibility.</p>
          </div>
          <div className="hp-grid hp-grid-3">
            <article className="hp-card"><h3>Prescription Management</h3><p>Track medication workflows and reduce manual errors.</p></article>
            <article className="hp-card"><h3>Inventory Control</h3><p>Monitor stock, batches, and expiry risk in real time.</p></article>
            <article className="hp-card"><h3>Patient Records</h3><p>Role-controlled access to patient data and updates.</p></article>
            <article className="hp-card"><h3>Analytics Dashboard</h3><p>Usable stock, expiry risk, and low-stock insights.</p></article>
            <article className="hp-card"><h3>Smart Notifications</h3><p>Proactive alerts for reorder, expiry, and workflow events.</p></article>
            <article className="hp-card"><h3>RBAC Security</h3><p>Permission-driven modules and action-level enforcement.</p></article>
          </div>
        </div>
      </section>

      <section className="hp-section hp-about" id="about">
        <div className="hp-container hp-grid hp-grid-2">
          <div>
            <div className="hp-tag">Why Healthora</div>
            <h2>The Problem We Are Solving</h2>
            <p>Traditional systems miss near-expiry and demand trends. HEALTHORA unifies stock, patient, and workflow visibility in one dashboard.</p>
            <p>It is designed to lower wastage, improve replenishment quality, and simplify daily pharmacy coordination.</p>
          </div>
          <div className="hp-stats">
            <div className="hp-stat"><strong>60%</strong><span>less manual data entry</span></div>
            <div className="hp-stat"><strong>3x</strong><span>faster stock review cycle</span></div>
            <div className="hp-stat"><strong>99.9%</strong><span>inventory accuracy target</span></div>
          </div>
        </div>
      </section>

      <section className="hp-section" id="team">
        <div className="hp-container">
          <div className="hp-header">
            <div className="hp-tag">Core Team</div>
            <h2>Meet the Builders</h2>
            <p>The team building HEALTHORA's predictive pharmacy platform.</p>
          </div>
          <div className="hp-grid hp-grid-4">
            <article className="hp-card hp-team"><h3>Akash Ani</h3><p>System Architecture</p></article>
            <article className="hp-card hp-team"><h3>Joel Joy</h3><p>AI and Data</p></article>
            <article className="hp-card hp-team"><h3>Jacob Biju</h3><p>Backend Engineering</p></article>
            <article className="hp-card hp-team"><h3>Ruben Roby</h3><p>Frontend Engineering</p></article>
          </div>
        </div>
      </section>

      <section className="hp-section hp-login-block" id="login">
        <div className="hp-container">
          <div className="hp-header">
            <h2>Sign In</h2>
            <p>Access your HEALTHORA dashboard</p>
          </div>
          <aside className="hp-login">
            <form onSubmit={handleSubmit}>
              <label>Username</label>
              <input className="input" placeholder="Enter username" value={username} onChange={(e) => setUsername(e.target.value)} required />

              <label>Password</label>
              <input className="input" type="password" placeholder="Enter password" value={password} onChange={(e) => setPassword(e.target.value)} required />

              <button type="submit" className="primary-btn" style={{ width: "100%" }}>Login</button>
            </form>
            {error ? <p className="error">{error}</p> : null}
            <div className="actions-cell" style={{ marginTop: 8 }}>
              <button type="button" className="secondary-btn compact" onClick={() => navigate("/login")}>Login Page</button>
              <a href="http://localhost:8000/docs" className="secondary-btn compact" target="_blank" rel="noreferrer">View Documentation</a>
            </div>
            <small>Users: sysadmin/admin, cmo1/cmo, pm1/manager, senior1/senior, staff1/staff, clerk1/clerk</small>
          </aside>
        </div>
      </section>

      <footer className="hp-footer">
        <div className="hp-container hp-footer-inner">
          <div className="hp-logo"><span className="hp-logo-box">H</span><span>HEALTH<span className="hp-primary">ORA</span></span></div>
          <p>© 2026 HEALTHORA. A Smart Pharmacy Management System.</p>
        </div>
      </footer>
    </div>
  );
}
