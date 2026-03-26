import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "./api";
import AuditModule from "./AuditModule";
import AIReportModule from "./AIReportModule";
import DispensingModule from "./DispensingModule";
import InventoryModule from "./InventoryModule";
import PatientsModule from "./PatientsModule";
import PrescriptionsModule from "./PrescriptionsModule";
import PurchaseOrdersModule from "./PurchaseOrdersModule";
import ReorderRecommendationModule from "./ReorderRecommendationModule";
import SuppliersModule from "./SuppliersModule";
import UsersModule from "./UsersModule";

const NAV = [
  { key: "dashboard", label: "Dashboard", icon: "📊" },
  { key: "patients", label: "Patients", icon: "🏥" },
  { key: "inventory", label: "Inventory", icon: "📦" },
  { key: "prescriptions", label: "Prescriptions", icon: "📋" },
  { key: "dispensing", label: "Dispensing", icon: "💉" },
  { key: "suppliers", label: "Suppliers", icon: "🏭" },
  { key: "purchase_orders", label: "Purchase Orders", icon: "🛒" },
  { key: "reorder_recommendation", label: "Reorder Recommendation", icon: "🔁" },
  { key: "users", label: "Users", icon: "👥" },
  { key: "audit", label: "Audit Log", icon: "🔍" },
  { key: "ai_report", label: "AI Report", icon: "🤖" },
];

function riskLevel(d) { return d < 0 ? "expired" : d <= 30 ? "high" : d <= 60 ? "medium" : "low"; }

function riskLabel(risk) {
  if (risk === "high") return "High Risk";
  if (risk === "medium") return "Medium Risk";
  if (risk === "low") return "Low Risk";
  if (risk === "expired") return "Expired";
  return risk;
}

const CARD_CFG = [
  { key: "usable_stock", label: "Usable Stock", icon: "📦", color: "#00d4d4", colorClass: "cyan", module: "inventory" },
  { key: "expiry_risk", label: "Expiry Risk 90d", icon: "⏳", color: "#ffe55c", colorClass: "amber", module: null },
  { key: "low_stock_alerts", label: "Low Stock Drugs", icon: "⚠️", color: "#ef233c", colorClass: "red", module: "inventory" },
  { key: "total_patients", label: "Active Patients", icon: "👤", color: "#8338ec", colorClass: "purple", module: "patients" },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState({ username: "", display_name: "", role: "" });
  const [modules, setModules] = useState(["dashboard"]);
  const [permissions, setPermissions] = useState([]);
  const [active, setActive] = useState("dashboard");

  const [summary, setSummary] = useState({});
  const [expiry, setExpiry] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [expiryDays, setExpiryDays] = useState(90);

  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [patients, setPatients] = useState([]);
  const [drugs, setDrugs] = useState([]);
  const [inventoryRows, setInventoryRows] = useState([]);
  const [suppliers, setSuppliers] = useState([]);

  const [globalError, setGlobalError] = useState("");
  const [loadingInit, setLoadingInit] = useState(true);

  const hasPermission = useCallback((p) => permissions.includes(p), [permissions]);
  const modulePermission = {
    patients: "view_patients",
    inventory: "view_inventory",
    prescriptions: "view_prescriptions",
    dispensing: "view_dispensing",
    suppliers: "view_suppliers",
    purchase_orders: "manage_inventory",
    reorder_recommendation: "manage_inventory",
    users: "manage_users",
    audit: "view_audit_logs",
    ai_report: "view_ai_report",
  };

  async function refreshDashboard() {
    const [sum, exp, notifs] = await Promise.all([
      api.dashboardSummary().catch(() => ({})),
      api.dashboardExpiry().catch(() => []),
      api.getNotifications().catch(() => []),
    ]);
    setSummary(sum); setExpiry(exp); setNotifications(notifs);
  }

  useEffect(() => {
    (async () => {
      try {
        const [me, access] = await Promise.all([api.me(), api.dashboardAccess()]);
        setProfile(me);
        setModules(access.modules || ["dashboard"]);
        setPermissions(access.permissions || []);
        await refreshDashboard();
      } catch { navigate("/"); }
      finally { setLoadingInit(false); }
    })();
  }, []);

  useEffect(() => {
    if (loadingInit) return;
    (async () => {
      try {
        if (active === "users") {
          const [u, r, d] = await Promise.all([api.getUsers(), api.getRoles(), api.getDepartments()]);
          setUsers(u); setRoles(r); setDepartments(d);
        }
        if (["patients", "prescriptions", "dispensing"].includes(active) && hasPermission("view_patients")) {
          setPatients(await api.getPatients());
        }
        if (["inventory", "prescriptions", "purchase_orders"].includes(active) && hasPermission("view_drugs")) {
          setDrugs(await api.getDrugs());
        }
        if (["inventory", "dispensing", "reorder_recommendation"].includes(active) && hasPermission("view_inventory")) {
          setInventoryRows(await api.getInventory());
        }
        if (["inventory", "purchase_orders"].includes(active) && hasPermission("view_suppliers")) {
          setSuppliers(await api.getSuppliers().catch(() => []));
        }
      } catch (e) { setGlobalError(e.message); }
    })();
  }, [active, hasPermission, loadingInit]);

  const filteredExpiry = useMemo(() =>
    expiry.map((r) => ({ ...r, risk: riskLevel(r.days_left) })).filter((r) => r.days_left <= expiryDays),
    [expiry, expiryDays]);

  const unread = notifications.filter((n) => !n.is_read).length;
  function switchModule(key) { setGlobalError(""); setActive(key); }

  async function markRead(id) { await api.markNotificationRead(id).catch(() => { }); await refreshDashboard(); }
  async function markAllRead() { await api.markAllNotificationsRead().catch(() => { }); await refreshDashboard(); }
  async function clearAll() { await api.clearNotifications().catch(() => { }); setNotifications([]); }
  function logout() {
    localStorage.clear();
    sessionStorage.clear();
    navigate("/");
  }

  const visibleNav = NAV.filter((n) => modules.includes(n.key) && (!modulePermission[n.key] || hasPermission(modulePermission[n.key])));
  const activeNav = NAV.find((n) => n.key === active);

  if (loadingInit) return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#f8f6ef" }}>
      <div style={{ textAlign: "center", border: "3px solid #0d0d0d", background: "#fff", padding: "40px 56px", boxShadow: "8px 8px 0 #0d0d0d" }}>
        <div style={{ fontSize: 52, marginBottom: 16 }}>💊</div>
        <div style={{ fontWeight: 800, fontSize: 20, letterSpacing: "0.06em", textTransform: "uppercase" }}>HEALTHORA</div>
        <div style={{ marginTop: 10, color: "#6b7280", fontWeight: 600 }}>Loading…</div>
      </div>
    </div>
  );

  return (
    <div className="app-shell">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">💊</div>
          <div className="brand-text">Healthora</div>
        </div>

        <nav className="side-nav">
          {visibleNav.map((n) => (
            <button
              key={n.key}
              type="button"
              className={`side-btn ${active === n.key ? "active" : ""}`}
              onClick={() => switchModule(n.key)}
            >
              <span className="nav-icon">{n.icon}</span>
              {n.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-card-sidebar">
            <div className="user-name">{profile.username}</div>
            <div className="user-role">{profile.display_name}</div>
          </div>
          <button className="danger-btn" style={{ width: "100%", justifyContent: "center", fontSize: 12 }} onClick={logout}>
            🚪 Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="main-panel">
        {/* Top bar */}
        <div className="top-header">
          <div>
            <h2>{activeNav?.icon} {activeNav?.label || "Dashboard"}</h2>
            <small>Signed in as <strong>{profile.username}</strong> · {profile.display_name}</small>
          </div>
          <div className="top-actions">
            {unread > 0 && (
              <span style={{
                background: "#fde0e3", border: "2px solid #ef233c",
                color: "#ef233c", padding: "5px 12px",
                fontSize: 12, fontWeight: 700, textTransform: "uppercase",
                letterSpacing: "0.05em", boxShadow: "2px 2px 0 #ef233c",
              }}>
                🔔 {unread} unread
              </span>
            )}
            <button className="secondary-btn compact" onClick={refreshDashboard}>↻</button>
          </div>
        </div>

        {globalError && (
          <div className="error-msg" style={{ margin: "16px 24px" }}>
            ⚠️ {globalError}
            <button onClick={() => setGlobalError("")} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", fontWeight: 700, color: "#b91c1c" }}>✕</button>
          </div>
        )}

        {/* ── DASHBOARD HOME ── */}
        {active === "dashboard" && (
          <>
            {/* Stat Cards */}
            <div className="cards">
              {CARD_CFG.map((cfg) => (
                modules.includes(cfg.module || "dashboard") || !cfg.module ? (
                  <div
                    className="card"
                    key={cfg.key}
                    style={{ cursor: (cfg.module && modules.includes(cfg.module)) ? "pointer" : "default" }}
                    onClick={() => cfg.module && modules.includes(cfg.module) && switchModule(cfg.module)}
                  >
                    <span className="card-icon">{cfg.icon}</span>
                    <h3>{cfg.label}</h3>
                    <div className={`card-value ${cfg.colorClass}`}>{summary[cfg.key] ?? 0}</div>
                    {cfg.module && modules.includes(cfg.module) && (
                      <div style={{ marginTop: 10, fontSize: 12, fontWeight: 700, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                        View Details →
                      </div>
                    )}
                  </div>
                ) : null
              ))}
            </div>

            {/* Expiry Risk Table */}
            <div className="section">
              <div className="section-header">
                <h3>⏳ Expiry Risk Monitor</h3>
                <div style={{ display: "flex", gap: 6 }}>
                  {[30, 60, 90].map((d) => (
                    <button key={d} className={`secondary-btn compact ${expiryDays === d ? "active-btn" : ""}`} onClick={() => setExpiryDays(d)}>
                      {d}d
                    </button>
                  ))}
                </div>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Drug</th><th>Batch No</th><th>Expiry</th><th>Days Left</th><th>Qty</th><th>Risk</th></tr>
                  </thead>
                  <tbody>
                    {filteredExpiry.length === 0 ? (
                      <tr>
                        <td colSpan={6} style={{ textAlign: "center", padding: "40px", color: "#9ca3af", fontWeight: 600 }}>
                          ✅ No items expiring within {expiryDays} days
                        </td>
                      </tr>
                    ) : filteredExpiry.map((row, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 700 }}>{row.drug_name}</td>
                        <td><code>{row.batch_no}</code></td>
                        <td>{row.expiry_date}</td>
                        <td style={{ fontWeight: 800, color: row.days_left < 0 ? "#ef233c" : row.days_left <= 30 ? "#d97706" : "#374151" }}>
                          {row.days_left < 0 ? "EXPIRED" : `${row.days_left}d`}
                        </td>
                        <td>{row.quantity_available}</td>
                        <td><span className={`badge ${row.risk}`}>{riskLabel(row.risk)}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Notifications */}
            <div className="section">
              <div className="section-header">
                <h3>🔔 Notifications {unread > 0 && <span style={{ color: "#ef233c", marginLeft: 8 }}>({unread} unread)</span>}</h3>
                <div style={{ display: "flex", gap: 6 }}>
                  {unread > 0 && <button className="secondary-btn compact" onClick={markAllRead}>Mark All Read</button>}
                  {notifications.length > 0 && <button className="danger-btn compact" onClick={clearAll}>Clear All</button>}
                </div>
              </div>
              {notifications.length === 0 ? (
                <div className="empty-state">
                  <span className="empty-icon">🔕</span>
                  No notifications — you're all caught up!
                </div>
              ) : (
                <ul className="notifications-list">
                  {notifications.map((n) => (
                    <li key={n.notification_id} className={n.is_read ? "read" : ""}>
                      <div>
                        <div className="notif-title">{n.title}</div>
                        <div className="notif-body">{n.message}</div>
                        <div className="notif-time">{String(n.created_at).slice(0, 16).replace("T", " ")}</div>
                      </div>
                      {!n.is_read && (
                        <button className="secondary-btn compact" onClick={() => markRead(n.notification_id)}>
                          Mark Read
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}

        {/* ── Modules ── */}
        {active === "users" && (
          <UsersModule users={users} roles={roles} departments={departments} hasPermission={hasPermission}
            onRefresh={async () => { const [u, r, d] = await Promise.all([api.getUsers(), api.getRoles(), api.getDepartments()]); setUsers(u); setRoles(r); setDepartments(d); }} />
        )}
        {active === "patients" && (
          <PatientsModule patients={patients} hasPermission={hasPermission}
            onRefresh={async () => { setPatients(await api.getPatients()); await refreshDashboard(); }} />
        )}
        {active === "inventory" && (
          <InventoryModule
            mode="inventory"
            drugs={drugs}
            inventoryRows={inventoryRows}
            suppliers={suppliers}
            hasPermission={hasPermission}
            onRefresh={async () => {
              const [i, d, s] = await Promise.all([
                api.getInventory(),
                api.getDrugs(),
                api.getSuppliers().catch(() => []),
              ]);
              setInventoryRows(i);
              setDrugs(d);
              setSuppliers(s);
              await refreshDashboard();
            }}
          />
        )}
        {active === "prescriptions" && (
          <PrescriptionsModule patients={patients} drugs={drugs} hasPermission={hasPermission} />
        )}
        {active === "dispensing" && (
          <DispensingModule patients={patients} inventoryRows={inventoryRows} hasPermission={hasPermission} />
        )}
        {active === "suppliers" && <SuppliersModule hasPermission={hasPermission} />}
        {active === "purchase_orders" && <PurchaseOrdersModule drugs={drugs} hasPermission={hasPermission} />}
        {active === "reorder_recommendation" && <ReorderRecommendationModule />}
        {active === "audit" && <AuditModule />}
        {active === "ai_report" && <AIReportModule />}
      </main>
    </div>
  );
}
