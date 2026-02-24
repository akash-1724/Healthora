import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "./api";

const moduleLabels = {
  dashboard: "Dashboard",
  users: "Users",
  patients: "Patients",
  drugs: "Drugs",
  inventory: "Inventory",
  ai_report: "AI Report",
  settings: "Settings",
};

const roleIcons = {
  usable_stock: "📦",
  total_stock: "🧾",
  expiry_risk: "⏳",
  low_stock_alerts: "⚠️",
  total_patients: "👥",
};

function riskLevel(daysLeft) {
  if (daysLeft <= 30) return "high";
  if (daysLeft <= 60) return "medium";
  return "low";
}

function batchStatus(daysLeft) {
  if (daysLeft < 0) return "expired";
  if (daysLeft <= 60) return "near-expiry";
  return "good";
}

export default function Dashboard() {
  const navigate = useNavigate();

  const [profile, setProfile] = useState({ username: "", display_name: "", role: "" });
  const [modules, setModules] = useState(["dashboard"]);
  const [permissions, setPermissions] = useState([]);
  const [activeModule, setActiveModule] = useState("dashboard");
  const [inventoryTab, setInventoryTab] = useState("drugs");

  const [summary, setSummary] = useState({ usable_stock: 0, total_stock: 0, expiry_risk: 0, low_stock_alerts: 0, total_patients: 0 });
  const [expiry, setExpiry] = useState([]);
  const [notifications, setNotifications] = useState([]);

  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [patients, setPatients] = useState([]);
  const [drugs, setDrugs] = useState([]);
  const [inventoryRows, setInventoryRows] = useState([]);

  const [globalSearch, setGlobalSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [aiMessage, setAiMessage] = useState("Coming soon");
  const [systemName, setSystemName] = useState(localStorage.getItem("systemName") || "HEALTHORA Smart Pharmacy");

  const [usersRoleFilter, setUsersRoleFilter] = useState("all");
  const [usersStatusFilter, setUsersStatusFilter] = useState("all");
  const [batchRiskFilter, setBatchRiskFilter] = useState("all");
  const [batchDrugFilter, setBatchDrugFilter] = useState("all");
  const [batchDaysFilter, setBatchDaysFilter] = useState("90");
  const [selectedExpiryDays, setSelectedExpiryDays] = useState(90);

  const [showUserModal, setShowUserModal] = useState(false);
  const [showPatientModal, setShowPatientModal] = useState(false);
  const [showDrugModal, setShowDrugModal] = useState(false);
  const [showBatchModal, setShowBatchModal] = useState(false);

  const [newUser, setNewUser] = useState({ username: "", password: "", role_id: "", department: "Pharmacy" });
  const [newPatient, setNewPatient] = useState({ first_name: "", last_name: "", contact: "" });
  const [newDrug, setNewDrug] = useState({ drug_name: "", generic_name: "", formulation: "Tablet", strength: "", schedule_type: "OTC" });
  const [newBatch, setNewBatch] = useState({ drug_id: "", batch_no: "", expiry_date: "", purchase_price: "", selling_price: "", quantity_available: "" });
  const [inventoryUpdate, setInventoryUpdate] = useState({ batch_id: "", quantity_available: "" });
  const [lowThresholds, setLowThresholds] = useState({});

  const hasPermission = (perm) => permissions.includes(perm);

  async function refreshDashboardWidgets() {
    const [summaryData, expiryData, notifData] = await Promise.all([api.dashboardSummary(), api.dashboardExpiry(), api.dashboardNotifications()]);
    setSummary(summaryData);
    setExpiry(expiryData);
    setNotifications((notifData || []).map((text, index) => ({ id: `${index}-${text}`, text, read: false })));
  }

  useEffect(() => {
    async function loadInitial() {
      setLoading(true);
      try {
        const [meData, accessData] = await Promise.all([api.me(), api.dashboardAccess()]);
        setProfile(meData);
        setModules(accessData.modules || ["dashboard"]);
        setPermissions(accessData.permissions || []);
        await refreshDashboardWidgets();
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadInitial();
  }, []);

  useEffect(() => {
    async function loadModuleData() {
      try {
        if (activeModule === "users") {
          const [u, r, d] = await Promise.all([api.getUsers(), api.getRoles(), api.getDepartments()]);
          setUsers(u);
          setRoles(r);
          setDepartments(d);
        }
        if (activeModule === "patients") {
          setPatients(await api.getPatients());
        }
        if (activeModule === "drugs") {
          setDrugs(await api.getDrugs());
        }
        if (activeModule === "inventory") {
          const [inv, d] = await Promise.all([api.getInventory(), api.getDrugs()]);
          setInventoryRows(inv);
          setDrugs(d);
        }
      } catch (err) {
        setError(err.message);
      }
    }
    loadModuleData();
  }, [activeModule]);

  const cards = useMemo(() => {
    const baseCards = [
      { key: "usable_stock", label: "Usable Stock", value: summary.usable_stock, detailsModule: "inventory" },
      { key: "total_stock", label: "Total Stock", value: summary.total_stock, detailsModule: "inventory" },
      { key: "expiry_risk", label: "Expiry Risk", value: summary.expiry_risk, detailsModule: "dashboard" },
      { key: "low_stock_alerts", label: "Low Stock Alerts", value: summary.low_stock_alerts, detailsModule: "inventory" },
    ];
    if (profile.role === "chief_medical_officer") {
      baseCards.push({ key: "total_patients", label: "Total Patients", value: summary.total_patients, detailsModule: "patients" });
    }
    return baseCards;
  }, [summary, profile.role]);

  const filteredExpiry = useMemo(
    () => expiry.filter((row) => row.days_left <= selectedExpiryDays).map((row) => ({ ...row, risk: riskLevel(row.days_left) })),
    [expiry, selectedExpiryDays]
  );

  const filteredUsers = useMemo(() => {
    const q = globalSearch.trim().toLowerCase();
    return users.filter((row) => {
      const roleMatches = usersRoleFilter === "all" || String(row.role_id) === usersRoleFilter;
      const statusMatches =
        usersStatusFilter === "all" ||
        (usersStatusFilter === "active" && row.is_active) ||
        (usersStatusFilter === "inactive" && !row.is_active);
      const searchMatches = !q || row.username.toLowerCase().includes(q);
      return roleMatches && statusMatches && searchMatches;
    });
  }, [users, usersRoleFilter, usersStatusFilter, globalSearch]);

  const filteredPatients = useMemo(() => {
    const q = globalSearch.trim().toLowerCase();
    return patients.filter((row) => !q || row.name.toLowerCase().includes(q) || (row.contact || "").toLowerCase().includes(q));
  }, [patients, globalSearch]);

  const inventoryJoined = useMemo(() => {
    const now = new Date();
    return inventoryRows.map((row) => {
      const daysLeft = Math.floor((new Date(row.expiry_date) - now) / (1000 * 60 * 60 * 24));
      return {
        ...row,
        days_left: daysLeft,
        status: batchStatus(daysLeft),
        risk: riskLevel(daysLeft),
      };
    });
  }, [inventoryRows]);

  const filteredBatchRows = useMemo(() => {
    const q = globalSearch.trim().toLowerCase();
    const filterDays = Number(batchDaysFilter);
    return inventoryJoined.filter((row) => {
      const drugMatches = batchDrugFilter === "all" || String(row.drug_id) === batchDrugFilter;
      const riskMatches = batchRiskFilter === "all" || row.risk === batchRiskFilter;
      const daysMatches = Number.isNaN(filterDays) || row.days_left <= filterDays;
      const searchMatches = !q || row.drug_name.toLowerCase().includes(q) || row.batch_no.toLowerCase().includes(q);
      return drugMatches && riskMatches && daysMatches && searchMatches;
    });
  }, [inventoryJoined, globalSearch, batchDrugFilter, batchRiskFilter, batchDaysFilter]);

  const stockViewRows = useMemo(() => {
    const grouped = {};
    for (const row of inventoryRows) {
      if (!grouped[row.drug_id]) {
        grouped[row.drug_id] = { drug_id: row.drug_id, drug_name: row.drug_name, total_stock: 0, active_batches: 0 };
      }
      grouped[row.drug_id].total_stock += row.quantity_available;
      grouped[row.drug_id].active_batches += 1;
    }
    return Object.values(grouped).map((row) => {
      const drug = drugs.find((item) => item.drug_id === row.drug_id);
      const threshold = Number(lowThresholds[row.drug_id] || drug?.low_stock_threshold || 50);
      return {
        ...row,
        threshold,
        low: row.total_stock < threshold,
      };
    });
  }, [inventoryRows, lowThresholds, drugs]);

  async function createUser(event) {
    event.preventDefault();
    try {
      await api.createUser({ ...newUser, role_id: Number(newUser.role_id), is_active: true });
      setShowUserModal(false);
      setNewUser({ username: "", password: "", role_id: "", department: "Pharmacy" });
      setUsers(await api.getUsers());
    } catch (err) {
      setError(err.message);
    }
  }

  async function createPatient(event) {
    event.preventDefault();
    try {
      const name = `${newPatient.first_name} ${newPatient.last_name}`.trim();
      await api.createPatient({ name, contact: newPatient.contact || null, gender: null, dob: null });
      setShowPatientModal(false);
      setNewPatient({ first_name: "", last_name: "", contact: "" });
      setPatients(await api.getPatients());
      await refreshDashboardWidgets();
    } catch (err) {
      setError(err.message);
    }
  }

  async function createDrug(event) {
    event.preventDefault();
    try {
      await api.createDrug(newDrug);
      setShowDrugModal(false);
      setNewDrug({ drug_name: "", generic_name: "", formulation: "Tablet", strength: "", schedule_type: "OTC" });
      setDrugs(await api.getDrugs());
    } catch (err) {
      setError(err.message);
    }
  }

  async function createBatch(event) {
    event.preventDefault();
    try {
      await api.createBatch({
        ...newBatch,
        drug_id: Number(newBatch.drug_id),
        purchase_price: Number(newBatch.purchase_price),
        selling_price: Number(newBatch.selling_price),
        quantity_available: Number(newBatch.quantity_available),
      });
      setShowBatchModal(false);
      setNewBatch({ drug_id: "", batch_no: "", expiry_date: "", purchase_price: "", selling_price: "", quantity_available: "" });
      setInventoryRows(await api.getInventory());
      await refreshDashboardWidgets();
    } catch (err) {
      setError(err.message);
    }
  }

  async function updateInventory(event) {
    event.preventDefault();
    try {
      await api.updateInventory(Number(inventoryUpdate.batch_id), { quantity_available: Number(inventoryUpdate.quantity_available) });
      setInventoryUpdate({ batch_id: "", quantity_available: "" });
      setInventoryRows(await api.getInventory());
      await refreshDashboardWidgets();
    } catch (err) {
      setError(err.message);
    }
  }

  async function generateAiReport() {
    try {
      const data = await api.aiReport();
      setAiMessage(data.message || "Coming soon");
    } catch (err) {
      setAiMessage("Coming soon");
      setError(err.message);
    }
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    localStorage.removeItem("displayName");
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("username");
    sessionStorage.removeItem("role");
    sessionStorage.removeItem("displayName");
    navigate("/");
  }

  function markNotificationRead(id) {
    setNotifications((prev) => prev.map((row) => (row.id === id ? { ...row, read: true } : row)));
  }

  function clearNotifications() {
    setNotifications([]);
  }

  function setDrugThreshold(drugId) {
    const value = window.prompt("Set low stock threshold", String(lowThresholds[drugId] || 50));
    if (value === null) return;
    const next = Number(value);
    if (Number.isNaN(next) || next < 0) return;
    api
      .updateDrug(drugId, { low_stock_threshold: next })
      .then(async () => {
        setLowThresholds((prev) => ({ ...prev, [drugId]: next }));
        setDrugs(await api.getDrugs());
        await refreshDashboardWidgets();
      })
      .catch((err) => setError(err.message));
  }

  async function editUser(row) {
    const nextDepartment = window.prompt("Update department", row.department || "Pharmacy");
    if (nextDepartment === null) return;
    try {
      await api.updateUser(row.user_id, { department: nextDepartment });
      setUsers(await api.getUsers());
    } catch (err) {
      setError(err.message);
    }
  }

  async function deactivateUser(row) {
    try {
      await api.deactivateUser(row.user_id);
      setUsers(await api.getUsers());
    } catch (err) {
      setError(err.message);
    }
  }

  async function resetPassword(row) {
    const nextPassword = window.prompt("Enter new password", "pass123");
    if (!nextPassword) return;
    try {
      await api.resetUserPassword(row.user_id, nextPassword);
      setUsers(await api.getUsers());
    } catch (err) {
      setError(err.message);
    }
  }

  async function deleteUser(row) {
    if (!window.confirm(`Delete user ${row.username}?`)) return;
    try {
      await api.deleteUser(row.user_id);
      setUsers(await api.getUsers());
    } catch (err) {
      setError(err.message);
    }
  }

  async function editPatient(row) {
    const nextName = window.prompt("Update patient name", row.name || "");
    if (!nextName) return;
    try {
      await api.updatePatient(row.patient_id, { name: nextName });
      setPatients(await api.getPatients());
    } catch (err) {
      setError(err.message);
    }
  }

  async function archivePatient(row) {
    if (!window.confirm(`Archive patient ${row.name}?`)) return;
    try {
      await api.archivePatient(row.patient_id);
      setPatients(await api.getPatients());
      await refreshDashboardWidgets();
    } catch (err) {
      setError(err.message);
    }
  }

  async function editDrug(row) {
    const nextStrength = window.prompt("Update strength", row.strength || "");
    if (nextStrength === null) return;
    try {
      await api.updateDrug(row.drug_id, { strength: nextStrength });
      setDrugs(await api.getDrugs());
    } catch (err) {
      setError(err.message);
    }
  }

  async function disableDrug(row) {
    if (!window.confirm(`Disable drug ${row.drug_name}?`)) return;
    try {
      await api.disableDrug(row.drug_id);
      setDrugs(await api.getDrugs());
    } catch (err) {
      setError(err.message);
    }
  }

  function openDrugBatches(drugId) {
    if (!hasPermission("view_inventory")) {
      setError("You can view drugs, but batch details require inventory access.");
      return;
    }
    setError("");
    setActiveModule("inventory");
    setInventoryTab("batches");
    setBatchDrugFilter(String(drugId));
  }

  async function markBatchExpired(row) {
    if (!window.confirm(`Mark batch ${row.batch_no} as expired?`)) return;
    try {
      await api.markBatchExpired(row.batch_id);
      setInventoryRows(await api.getInventory());
      await refreshDashboardWidgets();
    } catch (err) {
      setError(err.message);
    }
  }

  const roleTitle = useMemo(() => profile.display_name || profile.role || "User", [profile]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">HEALTHORA</div>
        <div className="side-nav">
          {modules.map((key) => (
            <button key={key} type="button" className={`side-btn ${activeModule === key ? "active" : ""}`} onClick={() => setActiveModule(key)}>
              {moduleLabels[key] || key}
            </button>
          ))}
        </div>
      </aside>

      <main className="main-panel">
        <div className="top-header">
          <div>
            <h2 style={{ margin: 0 }}>{systemName}</h2>
            <small>
              {profile.username} ({roleTitle})
            </small>
          </div>
          <div className="top-actions">
            <input className="input search-input" placeholder="Global search" value={globalSearch} onChange={(e) => setGlobalSearch(e.target.value)} />
            <button className="secondary-btn" onClick={() => navigate("/")}>Home</button>
            <button className="danger-btn" onClick={logout}>Logout</button>
          </div>
        </div>

        {loading ? <p>Loading...</p> : null}
        {error ? <p className="error">{error}</p> : null}

        {activeModule === "dashboard" && (
          <>
            <div className="cards">
              {cards.map((card) => (
                <div className="card" key={card.key}>
                  <h3>
                    {roleIcons[card.key]} {card.label}
                  </h3>
                  <p>{card.value}</p>
                  <small>+0% this week</small>
                  <button className="link-btn" type="button" onClick={() => setActiveModule(card.detailsModule)}>
                    View Details
                  </button>
                </div>
              ))}
            </div>

            <div className="section">
              <div className="section-header">
                <h3>Expiry Risk</h3>
                <div className="inline-controls">
                  {[30, 60, 90].map((days) => (
                    <button key={days} className={`secondary-btn compact ${selectedExpiryDays === days ? "active-btn" : ""}`} onClick={() => setSelectedExpiryDays(days)}>
                      {days} days
                    </button>
                  ))}
                </div>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Drug Name</th>
                      <th>Batch No</th>
                      <th>Expiry Date</th>
                      <th>Days Remaining</th>
                      <th>Quantity</th>
                      <th>Risk Level</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredExpiry.map((row) => (
                      <tr key={row.batch_no}>
                        <td>{row.drug_name}</td>
                        <td>{row.batch_no}</td>
                        <td>{row.expiry_date}</td>
                        <td>{row.days_left}</td>
                        <td>{row.quantity_available}</td>
                        <td><span className={`badge ${row.risk}`}>{row.risk}</span></td>
                        <td>
                          <button
                            className="secondary-btn compact"
                            onClick={() => {
                              setActiveModule("inventory");
                              setInventoryTab("batches");
                              setInventoryUpdate((prev) => ({ ...prev, batch_id: String(row.batch_id || "") }));
                            }}
                          >
                            View Batch
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="section">
              <div className="section-header">
                <h3>Notifications</h3>
                <button className="danger-btn compact" onClick={clearNotifications}>Clear All</button>
              </div>
              <ul className="notifications-list">
                {notifications.map((msg) => (
                  <li key={msg.id} className={msg.read ? "read" : ""}>
                    <span>{msg.text}</span>
                    <button className="secondary-btn compact" onClick={() => markNotificationRead(msg.id)}>Mark as Read</button>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}

        {activeModule === "users" && (
          <div className="section">
            <div className="section-header">
              <h3>User Management</h3>
              <button className="primary-btn" onClick={() => setShowUserModal(true)}>Add User</button>
            </div>
            <div className="inline-controls">
              <select className="input compact-input" value={usersRoleFilter} onChange={(e) => setUsersRoleFilter(e.target.value)}>
                <option value="all">All roles</option>
                {roles.map((role) => (
                  <option key={role.id} value={role.id}>{role.display_name}</option>
                ))}
              </select>
              <select className="input compact-input" value={usersStatusFilter} onChange={(e) => setUsersStatusFilter(e.target.value)}>
                <option value="all">Active + Inactive</option>
                <option value="active">Active only</option>
                <option value="inactive">Inactive only</option>
              </select>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Department</th>
                    <th>Status</th>
                    <th>Created At</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((row) => (
                    <tr key={row.user_id}>
                      <td>{row.username}</td>
                      <td>{row.role_display_name}</td>
                      <td>{row.department || "Pharmacy"}</td>
                      <td><span className={`badge ${row.is_active ? "good" : "high"}`}>{row.is_active ? "Active" : "Inactive"}</span></td>
                      <td>{String(row.created_at).slice(0, 10)}</td>
                      <td className="actions-cell">
                        <button className="secondary-btn compact" onClick={() => editUser(row)}>Edit</button>
                        <button className="secondary-btn compact" onClick={() => deactivateUser(row)}>Deactivate</button>
                        <button className="secondary-btn compact" onClick={() => resetPassword(row)}>Reset Password</button>
                        <button className="danger-btn compact" onClick={() => deleteUser(row)}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeModule === "patients" && (
          <div className="section">
            <div className="section-header">
              <h3>Patients</h3>
              {hasPermission("add_patients") ? <button className="primary-btn" onClick={() => setShowPatientModal(true)}>Add Patient</button> : null}
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Patient ID</th>
                    <th>Name</th>
                    <th>Contact</th>
                    <th>Created By</th>
                    <th>Created Date</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPatients.map((row) => (
                    <tr key={row.patient_id}>
                      <td>{row.patient_id}</td>
                      <td>{row.name}</td>
                      <td>{row.contact || "-"}</td>
                      <td>{row.created_by || "System"}</td>
                      <td>{String(row.created_at || "").slice(0, 10) || "-"}</td>
                      <td className="actions-cell">
                        <button className="secondary-btn compact">View Details</button>
                        <button className="secondary-btn compact" onClick={() => editPatient(row)}>Edit</button>
                        <button className="danger-btn compact" onClick={() => archivePatient(row)}>Archive</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeModule === "drugs" && (
          <div className="section">
            <div className="section-header">
              <h3>Drug Catalog</h3>
              {hasPermission("add_drug") ? <button className="primary-btn" onClick={() => setShowDrugModal(true)}>Add Drug</button> : null}
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Drug Name</th>
                    <th>Generic Name</th>
                    <th>Strength</th>
                    <th>Total Quantity</th>
                    <th>Active Batches</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {drugs
                    .filter((row) => !globalSearch || row.drug_name.toLowerCase().includes(globalSearch.toLowerCase()))
                    .map((drug) => {
                      return (
                        <tr key={drug.drug_id}>
                          <td>{drug.drug_name}</td>
                          <td>{drug.generic_name || "-"}</td>
                          <td>{drug.strength || "-"}</td>
                          <td>{drug.total_quantity ?? 0}</td>
                          <td>{drug.active_batches ?? 0}</td>
                          <td className="actions-cell">
                            <button className="secondary-btn compact" onClick={() => openDrugBatches(drug.drug_id)} disabled={!hasPermission("view_inventory")}>View Batches</button>
                            <button className="secondary-btn compact" disabled title="Temporarily disabled">Edit Drug</button>
                            <button className="danger-btn compact" disabled title="Temporarily disabled">Disable Drug</button>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeModule === "inventory" && (
          <div className="section">
            <div className="section-header">
              <h3>Inventory</h3>
              <div className="inline-controls">
                <button className={`secondary-btn compact ${inventoryTab === "drugs" ? "active-btn" : ""}`} onClick={() => setInventoryTab("drugs")}>Drugs</button>
                <button className={`secondary-btn compact ${inventoryTab === "batches" ? "active-btn" : ""}`} onClick={() => setInventoryTab("batches")}>Batches</button>
                <button className={`secondary-btn compact ${inventoryTab === "stock" ? "active-btn" : ""}`} onClick={() => setInventoryTab("stock")}>Stock View</button>
              </div>
            </div>

            {inventoryTab === "drugs" && (
              <>
                {hasPermission("add_drug") ? <button className="primary-btn" onClick={() => setShowDrugModal(true)}>Add Drug</button> : null}
                <div className="table-wrap" style={{ marginTop: 10 }}>
                  <table>
                    <thead>
                      <tr><th>Drug Name</th><th>Generic Name</th><th>Strength</th><th>Total Quantity</th><th>Active Batches</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                      {drugs.map((drug) => {
                        const rows = inventoryRows.filter((row) => row.drug_id === drug.drug_id);
                        return (
                          <tr key={drug.drug_id}>
                            <td>{drug.drug_name}</td><td>{drug.generic_name || "-"}</td><td>{drug.strength || "-"}</td>
                            <td>{rows.reduce((acc, row) => acc + row.quantity_available, 0)}</td><td>{rows.length}</td>
                            <td className="actions-cell"><button className="secondary-btn compact" onClick={() => { setInventoryTab("batches"); setBatchDrugFilter(String(drug.drug_id)); }}>View Batches</button></td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            {inventoryTab === "batches" && (
              <>
                <div className="inline-controls">
                  {hasPermission("add_batch") ? <button className="primary-btn" onClick={() => setShowBatchModal(true)}>Add Batch</button> : null}
                  <select className="input compact-input" value={batchDrugFilter} onChange={(e) => setBatchDrugFilter(e.target.value)}>
                    <option value="all">All Drugs</option>
                    {drugs.map((drug) => <option key={drug.drug_id} value={drug.drug_id}>{drug.drug_name}</option>)}
                  </select>
                  <select className="input compact-input" value={batchDaysFilter} onChange={(e) => setBatchDaysFilter(e.target.value)}>
                    <option value="30">30 days</option>
                    <option value="60">60 days</option>
                    <option value="90">90 days</option>
                    <option value="3650">All</option>
                  </select>
                  <select className="input compact-input" value={batchRiskFilter} onChange={(e) => setBatchRiskFilter(e.target.value)}>
                    <option value="all">All Risk</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
                <div className="table-wrap" style={{ marginTop: 10 }}>
                  <table>
                    <thead>
                      <tr><th>Drug</th><th>Batch No</th><th>Expiry Date</th><th>Quantity</th><th>Purchase Price</th><th>Status</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                      {filteredBatchRows.map((row) => (
                        <tr key={row.batch_id}>
                          <td>{row.drug_name}</td><td>{row.batch_no}</td><td>{row.expiry_date}</td><td>{row.quantity_available}</td><td>{row.purchase_price}</td>
                          <td><span className={`badge ${row.status === "expired" ? "high" : row.status === "near-expiry" ? "medium" : "good"}`}>{row.status}</span></td>
                          <td className="actions-cell">
                            {hasPermission("update_inventory") ? <button className="secondary-btn compact" onClick={() => setInventoryUpdate({ batch_id: String(row.batch_id), quantity_available: String(row.quantity_available) })}>Update Quantity</button> : null}
                            <button className="secondary-btn compact">View Details</button>
                            <button className="danger-btn compact" onClick={() => markBatchExpired(row)}>Mark Expired</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {hasPermission("update_inventory") ? (
                  <form onSubmit={updateInventory} style={{ marginTop: 12 }}>
                    <h4>Update Quantity</h4>
                    <input className="input" type="number" placeholder="Batch ID" value={inventoryUpdate.batch_id} onChange={(e) => setInventoryUpdate((prev) => ({ ...prev, batch_id: e.target.value }))} required />
                    <input className="input" type="number" placeholder="New Quantity" value={inventoryUpdate.quantity_available} onChange={(e) => setInventoryUpdate((prev) => ({ ...prev, quantity_available: e.target.value }))} required />
                    <button className="secondary-btn" type="submit">Save Quantity</button>
                  </form>
                ) : null}
              </>
            )}

            {inventoryTab === "stock" && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Drug Name</th><th>Total Stock</th><th>Low Stock Threshold</th><th>Status</th><th>Actions</th></tr>
                  </thead>
                  <tbody>
                    {stockViewRows.map((row) => (
                      <tr key={row.drug_id}>
                        <td>{row.drug_name}</td>
                        <td>{row.total_stock}</td>
                        <td>{row.threshold}</td>
                        <td><span className={`badge ${row.low ? "high" : "good"}`}>{row.low ? "Low" : "Good"}</span></td>
                        <td className="actions-cell">
                          {hasPermission("update_inventory") ? <button className="secondary-btn compact" onClick={() => setInventoryTab("batches")}>Adjust Stock</button> : null}
                          <button className="secondary-btn compact" onClick={() => setDrugThreshold(row.drug_id)}>Set Low Stock Threshold</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeModule === "ai_report" && (
          <div className="section">
            <h3>AI Report</h3>
            <button className="primary-btn" onClick={generateAiReport}>Generate Report</button>
            <p style={{ marginTop: 10 }}>{aiMessage}</p>
          </div>
        )}

        {activeModule === "settings" && (
          <div className="section">
            <h3>Settings</h3>
            <input className="input" value={systemName} onChange={(e) => setSystemName(e.target.value)} />
            <button className="primary-btn" onClick={() => localStorage.setItem("systemName", systemName)}>Update System Name</button>
            <div style={{ marginTop: 12 }} className="actions-cell">
              <button className="secondary-btn" onClick={() => setError("Manage roles coming soon")}>Manage Roles</button>
              <button className="secondary-btn" onClick={() => setError("Audit logs view-only coming soon")}>Audit Logs</button>
              <button className="secondary-btn" onClick={() => setError("Backup database stub coming soon")}>Backup Database</button>
            </div>
          </div>
        )}

        {showUserModal ? (
          <div className="modal-overlay">
            <div className="modal-card">
              <h3>Add User</h3>
              <form onSubmit={createUser}>
                <input className="input" placeholder="Username" value={newUser.username} onChange={(e) => setNewUser((prev) => ({ ...prev, username: e.target.value }))} required />
                <input className="input" placeholder="Password" value={newUser.password} onChange={(e) => setNewUser((prev) => ({ ...prev, password: e.target.value }))} required />
                <select className="input" value={newUser.role_id} onChange={(e) => setNewUser((prev) => ({ ...prev, role_id: e.target.value }))} required>
                  <option value="">Select Role</option>
                  {roles.map((role) => <option key={role.id} value={role.id}>{role.display_name}</option>)}
                </select>
                <select className="input" value={newUser.department} onChange={(e) => setNewUser((prev) => ({ ...prev, department: e.target.value }))} required>
                  <option value="">Select Department</option>
                  {departments.map((department) => <option key={department} value={department}>{department}</option>)}
                </select>
                <div className="actions-cell"><button className="primary-btn" type="submit">Save</button><button type="button" className="secondary-btn" onClick={() => setShowUserModal(false)}>Cancel</button></div>
              </form>
            </div>
          </div>
        ) : null}

        {showPatientModal ? (
          <div className="modal-overlay">
            <div className="modal-card">
              <h3>Add Patient</h3>
              <form onSubmit={createPatient}>
                <input className="input" placeholder="First Name" value={newPatient.first_name} onChange={(e) => setNewPatient((prev) => ({ ...prev, first_name: e.target.value }))} required />
                <input className="input" placeholder="Last Name" value={newPatient.last_name} onChange={(e) => setNewPatient((prev) => ({ ...prev, last_name: e.target.value }))} required />
                <input className="input" placeholder="Contact Number" value={newPatient.contact} onChange={(e) => setNewPatient((prev) => ({ ...prev, contact: e.target.value }))} required />
                <div className="actions-cell"><button className="primary-btn" type="submit">Save</button><button type="button" className="secondary-btn" onClick={() => setShowPatientModal(false)}>Cancel</button></div>
              </form>
            </div>
          </div>
        ) : null}

        {showDrugModal ? (
          <div className="modal-overlay">
            <div className="modal-card">
              <h3>Add Drug</h3>
              <form onSubmit={createDrug}>
                <input className="input" placeholder="Drug Name" value={newDrug.drug_name} onChange={(e) => setNewDrug((prev) => ({ ...prev, drug_name: e.target.value }))} required />
                <input className="input" placeholder="Generic Name" value={newDrug.generic_name} onChange={(e) => setNewDrug((prev) => ({ ...prev, generic_name: e.target.value }))} />
                <input className="input" placeholder="Strength" value={newDrug.strength} onChange={(e) => setNewDrug((prev) => ({ ...prev, strength: e.target.value }))} />
                <div className="actions-cell"><button className="primary-btn" type="submit">Save</button><button type="button" className="secondary-btn" onClick={() => setShowDrugModal(false)}>Cancel</button></div>
              </form>
            </div>
          </div>
        ) : null}

        {showBatchModal ? (
          <div className="modal-overlay">
            <div className="modal-card">
              <h3>Add Batch</h3>
              <form onSubmit={createBatch}>
                <select className="input" value={newBatch.drug_id} onChange={(e) => setNewBatch((prev) => ({ ...prev, drug_id: e.target.value }))} required>
                  <option value="">Select Drug</option>
                  {drugs.map((row) => <option key={row.drug_id} value={row.drug_id}>{row.drug_name}</option>)}
                </select>
                <input className="input" placeholder="Batch Number" value={newBatch.batch_no} onChange={(e) => setNewBatch((prev) => ({ ...prev, batch_no: e.target.value }))} required />
                <input className="input" type="date" value={newBatch.expiry_date} onChange={(e) => setNewBatch((prev) => ({ ...prev, expiry_date: e.target.value }))} required />
                <input className="input" type="number" placeholder="Quantity" value={newBatch.quantity_available} onChange={(e) => setNewBatch((prev) => ({ ...prev, quantity_available: e.target.value }))} required />
                <input className="input" type="number" step="0.01" placeholder="Purchase Price" value={newBatch.purchase_price} onChange={(e) => setNewBatch((prev) => ({ ...prev, purchase_price: e.target.value }))} required />
                <input className="input" type="number" step="0.01" placeholder="Selling Price" value={newBatch.selling_price} onChange={(e) => setNewBatch((prev) => ({ ...prev, selling_price: e.target.value }))} required />
                <div className="actions-cell"><button className="primary-btn" type="submit">Save</button><button type="button" className="secondary-btn" onClick={() => setShowBatchModal(false)}>Cancel</button></div>
              </form>
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
