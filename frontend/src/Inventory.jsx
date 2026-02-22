import React from "react";
import { useEffect, useState } from "react";

import { api } from "./api";

export default function Inventory() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    api
      .getInventory()
      .then((data) => {
        if (!mounted) return;
        setItems(data);
        setError("");
      })
      .catch(() => {
        if (!mounted) return;
        setError("Could not load inventory.");
      })
      .finally(() => mounted && setLoading(false));

    return () => (mounted = false);
  }, []);

  return (
    <div style={{ fontFamily: "Arial" }}>
      <h2 style={{ marginTop: 0 }}>Inventory</h2>
      <p style={{ color: "#475569" }}>Medicine batch list with quantity and pricing information.</p>

      <div style={{ overflowX: "auto", background: "white", border: "1px solid #dbe2ea", borderRadius: 12 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 700 }}>
          <thead style={{ background: "#eff6ff" }}>
            <tr>
              <th style={{ textAlign: "left", padding: 12 }}>Medicine Name</th>
              <th style={{ textAlign: "left", padding: 12 }}>Batch Number</th>
              <th style={{ textAlign: "left", padding: 12 }}>Expiry Date</th>
              <th style={{ textAlign: "left", padding: 12 }}>Quantity</th>
              <th style={{ textAlign: "left", padding: 12 }}>Unit Price</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ padding: 12 }}>
                  Loading...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={5} style={{ padding: 12, color: "#dc2626" }}>
                  {error}
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id} style={{ borderTop: "1px solid #eef2f7" }}>
                  <td style={{ padding: 12 }}>{item.name}</td>
                  <td style={{ padding: 12 }}>{item.batch}</td>
                  <td style={{ padding: 12 }}>{item.expiry}</td>
                  <td style={{ padding: 12 }}>{item.quantity}</td>
                  <td style={{ padding: 12 }}>{item.price !== undefined ? `Rs. ${item.price}` : "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 14, display: "flex", gap: 10 }}>
        <button type="button" style={{ padding: "9px 14px", border: "none", borderRadius: 8, background: "#2563eb", color: "white", cursor: "pointer" }}>
          Add New Batch
        </button>
        <button type="button" style={{ padding: "9px 14px", border: "none", borderRadius: 8, background: "#0ea5e9", color: "white", cursor: "pointer" }}>
          Save
        </button>
      </div>
    </div>
  );
}
