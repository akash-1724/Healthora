import React from "react";
import { useNavigate } from "react-router-dom";

const FEATURES = [
  { icon: "📋", title: "Prescriptions", desc: "Track medication workflows, link prescriptions to dispensing, eliminate manual errors.", color: "#ccf7f7" },
  { icon: "📦", title: "Inventory", desc: "Monitor stock, batches, and expiry risk in real time with auto-expiry flagging.", color: "#fff9cc" },
  { icon: "🏥", title: "Patients", desc: "Role-controlled access to patient data, history, and registration.", color: "#e8d9fc" },
  { icon: "🛒", title: "Purchase Orders", desc: "Manage supplier relationships and full purchase order lifecycle.", color: "#ffe3d8" },
  { icon: "🔔", title: "Notifications", desc: "Proactive alerts for reorder, expiry, and critical workflow events.", color: "#ccf5ea" },
  { icon: "🔍", title: "Audit Log", desc: "Full action-level trail for compliance and security reviews.", color: "#fde0e3" },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="hp-root">
      {/* ── Navbar ── */}
      <header className="hp-nav-wrap">
        <div className="hp-container hp-nav">
          <div className="hp-logo">
            <div className="hp-brand-icon">💊</div>
            <span className="hp-brand-name">HEALTHORA</span>
          </div>
          <nav className="hp-links">
            <a href="#features" className="hp-btn">Features</a>
            <a href="#about" className="hp-btn">About</a>
            <button className="hp-btn hp-btn-primary" onClick={() => navigate("/login")}>Sign In →</button>
          </nav>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="hp-hero" id="home">
        <div className="hp-container">
          <div className="hp-tag">🚀 Smart Pharmacy Platform</div>
          <h1 className="hp-hero-title">
            Pharmacy<br /><span className="grad">Management,</span><br />Reimagined.
          </h1>
          <p className="hp-hero-sub">
            HEALTHORA unifies inventory, prescriptions, patient records, and supply chain in one secure, role-based platform — built for hospital pharmacies.
          </p>
          <div className="hp-actions">
            <button className="hp-btn hp-btn-primary" style={{ padding: "12px 28px", fontSize: 15 }} onClick={() => navigate("/login")}>
              → Get Started
            </button>
            <a href="#features" className="hp-btn" style={{ padding: "12px 24px", fontSize: 15 }}>
              Explore Features
            </a>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="hp-section" id="features" style={{ borderTop: "3px solid #0d0d0d" }}>
        <div className="hp-container">
          <div className="hp-header">
            <div className="hp-tag">What It Does</div>
            <h2>System <span style={{ color: "#0094a1" }}>Capabilities</span></h2>
            <p>Core modules built for pharmacy operations, inventory safety, and clinical visibility.</p>
          </div>
          <div className="hp-grid hp-grid-3">
            {FEATURES.map((f) => (
              <article className="hp-card" key={f.title} style={{ background: f.color }}>
                <span className="hp-card-icon">{f.icon}</span>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── About ── */}
      <section className="hp-section" id="about" style={{ background: "#fff", borderTop: "3px solid #0d0d0d", borderBottom: "3px solid #0d0d0d" }}>
        <div className="hp-container">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 48, alignItems: "start" }}>
            <div>
              <div className="hp-tag">Why Healthora</div>
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 44px)", fontWeight: 900, letterSpacing: "-0.03em", marginTop: 16, marginBottom: 16, lineHeight: 1.1 }}>
                The Problem<br />We Are Solving
              </h2>
              <p style={{ color: "#4b5563", fontWeight: 500, lineHeight: 1.75, marginBottom: 12 }}>
                Traditional systems miss near-expiry signals and demand trends. HEALTHORA unifies stock, patient, and workflow visibility in one real-time dashboard.
              </p>
              <p style={{ color: "#4b5563", fontWeight: 500, lineHeight: 1.75 }}>
                Designed to lower wastage, improve replenishment quality, and simplify daily pharmacy coordination.
              </p>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[
                ["60%", "less manual data entry", "#ccf7f7"],
                ["3×", "faster stock review cycle", "#fff9cc"],
                ["99.9%", "inventory accuracy target", "#ccf5ea"],
              ].map(([stat, label, bg]) => (
                <div className="hp-stat" key={stat} style={{ background: bg }}>
                  <strong>{stat}</strong>
                  <span>{label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <div className="hp-login-block" id="login">
        <div className="hp-container" style={{ textAlign: "center" }}>
          <div className="hp-tag" style={{ margin: "0 auto 20px", background: "#ffe55c" }}>
            Ready to start?
          </div>
          <h2 style={{ color: "#fff", fontSize: "clamp(28px, 5vw, 64px)", fontWeight: 900, letterSpacing: "-0.03em", marginBottom: 14 }}>
            Access Your Dashboard
          </h2>
          <p style={{ color: "rgba(255,255,255,0.6)", fontWeight: 500, fontSize: 17, marginBottom: 32 }}>
            Sign in to manage your pharmacy operations.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <button
              className="hp-btn"
              style={{ padding: "14px 32px", fontSize: 15, background: "#00d4d4", boxShadow: "5px 5px 0 #00d4d4" }}
              onClick={() => navigate("/login")}
            >
              → Sign In to Healthora
            </button>
            <a
              href="http://localhost:8000/docs"
              className="hp-btn"
              style={{ padding: "14px 24px", fontSize: 15, background: "#fff", color: "#0d0d0d" }}
              target="_blank"
              rel="noreferrer"
            >
              📖 API Docs
            </a>
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer className="hp-footer">
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div className="hp-logo">
            <div className="hp-brand-icon" style={{ width: 28, height: 28, fontSize: 14 }}>💊</div>
            <span className="hp-brand-name" style={{ fontSize: 16 }}>HEALTHORA</span>
          </div>
          <p style={{ color: "#9ca3af", fontSize: 13, fontWeight: 600 }}>© 2026 HEALTHORA — Smart Pharmacy Management System</p>
        </div>
      </footer>
    </div>
  );
}
