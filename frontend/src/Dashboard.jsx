import React from "react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "./api";

const expiryRisk = [
  "Amoxicillin (Batch A-5620) - expires in 27 days",
  "Paracetamol (Batch P-1001) - expires in 53 days",
  "Cetirizine (Batch C-3022) - expires in 200 days",
];

const notifications = ["Expiry Alert", "Reorder Suggestion", "Info Message"];

export default function Dashboard() {
  const role = localStorage.getItem("role");
  const [totalStock, setTotalStock] = useState(null);
  const [totalItems, setTotalItems] = useState(null);

  useEffect(() => {
    api
      .getInventory()
      .then((items) => {
        const stock = items.reduce((sum, item) => sum + item.quantity, 0);
        setTotalStock(stock);
        setTotalItems(items.length);
      })
      .catch(() => {
        setTotalStock("N/A");
        setTotalItems("N/A");
      });
  }, []);

  return (
    <div style={{ fontFamily: "Arial" }}>
      <h2 style={{ marginTop: 0 }}>Dashboard</h2>
      <p style={{ color: "#475569" }}>Overview of medicine stock, expiry risk, and notifications.</p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 14, marginTop: 16 }}>
        <div style={{ background: "#e0f2fe", border: "1px solid #bae6fd", borderRadius: 12, padding: 16 }}>
          <h3 style={{ marginTop: 0 }}>Usable Stock</h3>
          <p style={{ margin: "8px 0", fontSize: 18 }}>
            Total Units: <b>{totalStock !== null ? totalStock : "Loading..."}</b>
          </p>
          <p style={{ margin: "8px 0", fontSize: 18 }}>
            Medicines: <b>{totalItems !== null ? totalItems : "Loading..."}</b>
          </p>
          <Link to="/inventory">
            <button type="button" style={{ marginTop: 8, padding: "8px 12px", border: "none", borderRadius: 8, background: "#0284c7", color: "white", cursor: "pointer" }}>
              View Stock Details
            </button>
          </Link>
        </div>

        <div style={{ background: "#fef9c3", border: "1px solid #fde68a", borderRadius: 12, padding: 16 }}>
          <h3 style={{ marginTop: 0 }}>Expiry Risk</h3>
          <ul style={{ paddingLeft: 18, margin: "10px 0" }}>
            {expiryRisk.map((item) => (
              <li key={item} style={{ marginBottom: 8 }}>
                {item}
              </li>
            ))}
          </ul>
          <button type="button" style={{ padding: "8px 12px", border: "none", borderRadius: 8, background: "#ca8a04", color: "white", cursor: "pointer" }}>
            Mark as Reviewed
          </button>
        </div>

        <div style={{ background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: 12, padding: 16 }}>
          <h3 style={{ marginTop: 0 }}>Notifications</h3>
          {notifications.map((msg) => (
            <p key={msg} style={{ margin: "10px 0" }}>
              {msg === "Info Message" ? "ℹ️" : "⚠️"} {msg}
            </p>
          ))}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" style={{ padding: "8px 12px", border: "none", borderRadius: 8, background: "#334155", color: "white", cursor: "pointer" }}>
              Open Alerts
            </button>
            <button type="button" style={{ padding: "8px 12px", border: "1px solid #334155", borderRadius: 8, background: "white", color: "#334155", cursor: "pointer" }}>
              Dismiss All
            </button>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 20, display: "flex", gap: 10, flexWrap: "wrap" }}>
        <Link to="/inventory" style={{ textDecoration: "none", padding: "10px 14px", background: "#2563eb", color: "white", borderRadius: 8 }}>
          Go to Inventory
        </Link>
        {role === "admin" && (
          <Link to="/users" style={{ textDecoration: "none", padding: "10px 14px", background: "#0ea5e9", color: "white", borderRadius: 8 }}>
            Go to Users
          </Link>
        )}
      </div>
    </div>
  );
}
