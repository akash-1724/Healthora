import React from "react";

const reorderRows = [
  { medicine: "Paracetamol", current: 40, usage: 65, recommend: 80 },
  { medicine: "Amoxicillin", current: 22, usage: 50, recommend: 70 },
  { medicine: "Insulin", current: 15, usage: 25, recommend: 30 },
];

export default function Reorder() {
  return (
    <div style={{ fontFamily: "Arial" }}>
      <h2 style={{ marginTop: 0 }}>Reorder</h2>
      <p style={{ color: "#475569" }}>Suggested reorder quantities based on sample predicted usage.</p>

      <div style={{ overflowX: "auto", background: "white", border: "1px solid #dbe2ea", borderRadius: 12 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 700 }}>
          <thead style={{ background: "#ecfeff" }}>
            <tr>
              <th style={{ textAlign: "left", padding: 12 }}>Medicine</th>
              <th style={{ textAlign: "left", padding: 12 }}>Current Stock</th>
              <th style={{ textAlign: "left", padding: 12 }}>Predicted Usage</th>
              <th style={{ textAlign: "left", padding: 12 }}>Recommended Order</th>
              <th style={{ textAlign: "left", padding: 12 }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {reorderRows.map((row) => (
              <tr key={row.medicine} style={{ borderTop: "1px solid #eef2f7" }}>
                <td style={{ padding: 12 }}>{row.medicine}</td>
                <td style={{ padding: 12 }}>{row.current}</td>
                <td style={{ padding: 12 }}>{row.usage}</td>
                <td style={{ padding: 12 }}>{row.recommend}</td>
                <td style={{ padding: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button type="button" style={{ padding: "7px 10px", border: "none", borderRadius: 8, background: "#2563eb", color: "white", cursor: "pointer" }}>
                    Order Now
                  </button>
                  <button type="button" style={{ padding: "7px 10px", border: "none", borderRadius: 8, background: "#0ea5e9", color: "white", cursor: "pointer" }}>
                    Adjust Quantity
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button type="button" style={{ marginTop: 14, padding: "10px 14px", border: "none", borderRadius: 8, background: "#0f766e", color: "white", cursor: "pointer" }}>
        Generate Purchase Order
      </button>
    </div>
  );
}
