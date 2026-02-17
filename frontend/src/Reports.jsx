import React from "react";
import { useState } from "react";

export default function Reports() {
  const [question, setQuestion] = useState("");

  return (
    <div style={{ fontFamily: "Arial" }}>
      <h2 style={{ marginTop: 0 }}>Reports</h2>
      <p style={{ color: "#475569" }}>AI Reporting with natural language questions.</p>

      <div style={{ background: "white", border: "1px solid #dbe2ea", borderRadius: 12, padding: 16, maxWidth: 720 }}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question in natural language..."
          style={{ width: "100%", padding: 11, borderRadius: 8, border: "1px solid #d1d5db", marginBottom: 10 }}
        />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button type="button" style={{ padding: "9px 12px", border: "none", borderRadius: 8, background: "#2563eb", color: "white", cursor: "pointer" }}>
            Ask
          </button>
          <button type="button" style={{ padding: "9px 12px", border: "none", borderRadius: 8, background: "#0ea5e9", color: "white", cursor: "pointer" }}>
            Generate Report
          </button>
          <button type="button" style={{ padding: "9px 12px", border: "1px solid #2563eb", borderRadius: 8, background: "white", color: "#2563eb", cursor: "pointer" }}>
            Export PDF
          </button>
        </div>
      </div>
    </div>
  );
}
