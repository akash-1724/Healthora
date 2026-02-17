import React from "react";
import { useState } from "react";

const sampleBatches = [
  { id: 1, medicine: "Paracetamol", batch: "P-1001", expiry: "2026-04-15", quantity: 240, price: "12.50" },
  { id: 2, medicine: "Amoxicillin", batch: "A-5620", expiry: "2026-03-20", quantity: 130, price: "18.00" },
  { id: 3, medicine: "Cetirizine", batch: "C-3022", expiry: "2026-09-10", quantity: 95, price: "9.75" },
];

export default function Inventory() {
  const [items] = useState(sampleBatches);

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
            {items.map((item) => (
              <tr key={item.id} style={{ borderTop: "1px solid #eef2f7" }}>
                <td style={{ padding: 12 }}>{item.medicine}</td>
                <td style={{ padding: 12 }}>{item.batch}</td>
                <td style={{ padding: 12 }}>{item.expiry}</td>
                <td style={{ padding: 12 }}>{item.quantity}</td>
                <td style={{ padding: 12 }}>Rs. {item.price}</td>
              </tr>
            ))}
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
