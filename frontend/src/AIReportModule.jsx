import React, { useMemo, useState } from "react";
import { api } from "./api";

function SimpleChart({ chart }) {
  const labels = chart?.labels || [];
  const values = chart?.series?.[0]?.values || [];
  const maxVal = Math.max(...values, 1);
  const points = values.map((v, i) => {
    const x = labels.length <= 1 ? 10 : (i / (labels.length - 1)) * 100;
    const y = 90 - (v / maxVal) * 80;
    return `${x},${y}`;
  });

  if (!values.length) return null;

  if (chart.type === "bar") {
    return (
      <div style={{ display: "grid", gap: 6 }}>
        {values.map((value, idx) => (
          <div key={idx} style={{ display: "grid", gridTemplateColumns: "140px 1fr 70px", alignItems: "center", gap: 8 }}>
            <div style={{ fontSize: 12, color: "#4b5563", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{labels[idx]}</div>
            <div style={{ height: 10, background: "#e5e7eb", borderRadius: 999 }}>
              <div style={{ width: `${(value / maxVal) * 100}%`, height: "100%", background: "#0ea5e9", borderRadius: 999 }} />
            </div>
            <div style={{ fontSize: 12, fontWeight: 700, textAlign: "right" }}>{value}</div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div>
      <svg viewBox="0 0 100 100" style={{ width: "100%", maxHeight: 220, background: "#f9fafb", border: "1px solid #d1d5db" }}>
        <polyline fill="none" stroke="#0891b2" strokeWidth="2" points={points.join(" ")} />
        {points.map((pt, idx) => {
          const [x, y] = pt.split(",");
          return <circle key={idx} cx={x} cy={y} r="1.5" fill="#0f172a" />;
        })}
      </svg>
      <div style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}>
        {labels.map((label, idx) => (
          <span key={idx} style={{ fontSize: 11, color: "#6b7280", border: "1px solid #d1d5db", padding: "2px 6px", borderRadius: 999 }}>
            {label}: {values[idx]}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function AIReportModule() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");
  const [format, setFormat] = useState("pdf");
  const [report, setReport] = useState(null);

  const previewRows = useMemo(() => (report?.rows || []).slice(0, 120), [report]);

  async function generateReport() {
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.aiGenerateReport(question.trim());
      setReport(data);
    } catch (e) {
      setError(e.message || "Failed to generate report");
      setReport(null);
    } finally {
      setLoading(false);
    }
  }

  async function downloadReport() {
    if (!report?.report_id) return;
    setDownloading(true);
    setError("");
    try {
      const blob = await api.aiDownloadReport(report.report_id, format);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${report.report_id}.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message || "Download failed");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="section" style={{ margin: 24 }}>
      <div className="section-header"><h3>AI Report Studio</h3></div>

      <div style={{ display: "grid", gap: 12 }}>
        <textarea
          rows={3}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Example: Generate a report of sales of paracetamol in the past 1 year"
          style={{ width: "100%", border: "2px solid #111827", padding: 12, fontSize: 14, background: "#fff", resize: "vertical" }}
        />
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button className="primary-btn" onClick={generateReport} disabled={loading}>{loading ? "Generating..." : "Generate Preview"}</button>
          <select value={format} onChange={(e) => setFormat(e.target.value)} style={{ border: "2px solid #111827", padding: "8px 10px", background: "#fff", fontWeight: 700 }}>
            <option value="pdf">PDF</option>
            <option value="csv">CSV</option>
          </select>
          <button className="secondary-btn" onClick={downloadReport} disabled={!report || downloading}>{downloading ? "Downloading..." : "Download"}</button>
          {report?.cached && <span className="badge low">cached</span>}
        </div>
      </div>

      {error && <div className="error-msg" style={{ marginTop: 12 }}>⚠️ {error}</div>}

      {report && (
        <>
          <div style={{ marginTop: 14, border: "1px solid #d1d5db", background: "#f9fafb", padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: "0.05em", color: "#6b7280", textTransform: "uppercase" }}>Executive Summary</div>
            <div style={{ marginTop: 8, color: "#111827", lineHeight: 1.5 }}>{report.summary_text}</div>
          </div>

          <div className="cards" style={{ marginTop: 12 }}>
            {(report.kpis || []).map((kpi, idx) => (
              <div className="card" key={idx}>
                <h3 style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em", color: "#6b7280" }}>{kpi.label}</h3>
                <div className="card-value cyan">{kpi.value}</div>
              </div>
            ))}
          </div>

          {(report.charts || []).length > 0 && (
            <div className="section" style={{ marginTop: 12 }}>
              <div className="section-header"><h3>Preview Graphs</h3></div>
              <div style={{ display: "grid", gap: 12 }}>
                {report.charts.map((chart, idx) => (
                  <div key={idx} style={{ border: "1px solid #d1d5db", background: "#fff", padding: 12 }}>
                    <div style={{ fontSize: 13, fontWeight: 800, marginBottom: 8 }}>{chart.title}</div>
                    <SimpleChart chart={chart} />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ marginTop: 14 }}>
            <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em", color: "#6b7280", fontWeight: 700 }}>Generated SQL</div>
            <pre style={{ whiteSpace: "pre-wrap", background: "#f9fafb", border: "1px solid #d1d5db", padding: 10, fontSize: 12, overflowX: "auto" }}>{report.sql}</pre>
          </div>

          <div className="table-wrap" style={{ marginTop: 12 }}>
            <table>
              <thead>
                <tr>{(report.columns || []).map((col) => <th key={col}>{col}</th>)}</tr>
              </thead>
              <tbody>
                {previewRows.length === 0 ? (
                  <tr>
                    <td colSpan={Math.max((report.columns || []).length, 1)} style={{ textAlign: "center", padding: 24, color: "#6b7280" }}>No rows returned</td>
                  </tr>
                ) : previewRows.map((row, idx) => (
                  <tr key={idx}>{row.map((value, i) => <td key={`${idx}-${i}`}>{String(value ?? "")}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
