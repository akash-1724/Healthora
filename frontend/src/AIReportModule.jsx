import React, { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "./api";

function isNumeric(value) {
  return value !== null && value !== "" && !Number.isNaN(Number(value));
}

function ChartsPanel({ columns, rows }) {
  if (!rows || rows.length === 0 || !columns || columns.length === 0) return null;

  const sample = rows[0] || [];
  const labelIndex = columns.findIndex((_, idx) => !isNumeric(sample[idx]));
  const valueIndex = columns.findIndex((_, idx) => isNumeric(sample[idx]));
  if (labelIndex === -1 || valueIndex === -1) return null;

  const labelColumn = columns[labelIndex];
  const valueColumn = columns[valueIndex];
  const chartData = rows.slice(0, 15).map((row) => {
    const label = String(row[labelIndex] ?? "");
    return {
      name: label.length > 15 ? `${label.slice(0, 15)}...` : label,
      value: Number(row[valueIndex]),
    };
  });

  return (
    <div style={{ display: "grid", gap: 12, gridTemplateColumns: "1fr 1fr", marginTop: 12 }}>
      <div style={{ background: "#fff", border: "1px solid #d1d5db", borderRadius: 8, padding: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>{valueColumn} by {labelColumn}</div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="value" fill="#22c55e" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ background: "#fff", border: "1px solid #d1d5db", borderRadius: 8, padding: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Trend of {valueColumn}</div>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#0ea5e9" strokeWidth={2} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function AIReportModule() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [searched, setSearched] = useState(false);

  const [report, setReport] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [format, setFormat] = useState("pdf");

  const previewRows = useMemo(() => (result?.rows || []).slice(0, 150), [result]);

  async function runQuery() {
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    setSearched(true);
    setReport(null);

    try {
      const data = await api.aiReportQuery(question.trim());
      setResult(data);
    } catch (err) {
      setError(err.message || "Failed to run query");
    } finally {
      setLoading(false);
    }
  }

  async function generateDownloadableReport() {
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.aiGenerateReport(question.trim());
      setReport(data);
    } catch (err) {
      setError(err.message || "Failed to generate downloadable report");
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
    } catch (err) {
      setError(err.message || "Download failed");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="section" style={{ margin: 24 }}>
      <div className="section-header"><h3>AI Query Console</h3></div>

      <div style={{ display: "grid", gap: 10 }}>
        <textarea
          rows={3}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) runQuery();
          }}
          placeholder="Ask in plain English. Example: show top dispensed medicines by month"
          style={{ width: "100%", border: "2px solid #111827", padding: 12, fontSize: 14, background: "#fff", resize: "vertical" }}
        />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <button className="primary-btn" onClick={runQuery} disabled={loading}>{loading ? "Running..." : "Run Query"}</button>
          <button className="secondary-btn" onClick={generateDownloadableReport} disabled={loading || !result}>{loading ? "Preparing..." : "Prepare Download"}</button>
          {result?.cached && <span className="badge good">Cached (RAG)</span>}
          {result && <span className="badge medium">{result.count} rows</span>}
        </div>
      </div>

      {error && <div className="error-msg" style={{ marginTop: 12 }}>⚠️ {error}</div>}

      {loading && <p style={{ marginTop: 12, color: "#64748b" }}>Searching database...</p>}

      {result && (
        <>
          <ChartsPanel columns={result.columns} rows={result.rows} />

          <div style={{ marginTop: 12, background: "#111827", color: "#e5e7eb", padding: 12, borderRadius: 8, fontFamily: "monospace", fontSize: 12 }}>
            <div style={{ color: "#86efac", marginBottom: 6, fontSize: 11 }}>Generated SQL</div>
            <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{result.sql}</pre>
          </div>

          <div className="table-wrap" style={{ marginTop: 12 }}>
            <table>
              <thead>
                <tr>{(result.columns || []).map((col) => <th key={col}>{col}</th>)}</tr>
              </thead>
              <tbody>
                {previewRows.length === 0 ? (
                  <tr><td colSpan={Math.max((result.columns || []).length, 1)} style={{ textAlign: "center", padding: 24 }}>No rows returned</td></tr>
                ) : previewRows.map((row, idx) => (
                  <tr key={idx}>{row.map((value, i) => <td key={`${idx}-${i}`}>{value == null ? "NULL" : String(value)}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>

          {report && (
            <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
              <select value={format} onChange={(e) => setFormat(e.target.value)} className="input compact-input" style={{ width: 120 }}>
                <option value="pdf">PDF</option>
                <option value="csv">CSV</option>
              </select>
              <button className="secondary-btn" onClick={downloadReport} disabled={downloading}>{downloading ? "Downloading..." : "Download"}</button>
            </div>
          )}
        </>
      )}

      {!loading && !result && searched && !error && (
        <div style={{ marginTop: 12, color: "#64748b" }}>No result returned for this query.</div>
      )}
    </div>
  );
}
