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

const SKIP_NAMES = [
  "_id",
  " id",
  "record_id",
  "batch_id",
  "drug_id",
  "patient_id",
  "po_id",
  "item_id",
  "prescription_id",
  "id",
];

function isIdColumn(name) {
  const lower = String(name || "").toLowerCase();
  return SKIP_NAMES.some((token) => lower.endsWith(token));
}

function scoreName(name, tokens) {
  const lower = String(name || "").toLowerCase();
  return tokens.some((t) => lower.includes(t));
}

function isChartWorthwhile(columns, rows) {
  if (!rows || rows.length <= 1) return false;

  const stringCandidates = columns
    .map((col, idx) => ({ col, idx }))
    .filter(({ col, idx }) => !isIdColumn(col) && rows.some((row) => typeof row[idx] === "string" && String(row[idx]).trim()));
  if (!stringCandidates.length) return false;

  const categoryIndex = stringCandidates[0].idx;
  const distinct = new Set(rows.map((row) => String(row[categoryIndex] ?? "").trim()).filter(Boolean));
  if (distinct.size < 2) return false;

  const numericNonId = columns
    .map((col, idx) => ({ col, idx }))
    .filter(({ col, idx }) => !isIdColumn(col) && rows.some((row) => isNumeric(row[idx])));
  if (!numericNonId.length) return false;

  return true;
}

function buildChartData(columns, rows, chartHint = "auto") {
  if (!rows.length || !columns.length) return null;

  const numericCandidates = columns
    .map((col, idx) => ({ col, idx }))
    .filter(({ col, idx }) => rows.some((row) => isNumeric(row[idx])) && !isIdColumn(col) && !scoreName(col, ["code"]));
  if (!numericCandidates.length) return null;

  const valueCandidate = numericCandidates.find(({ col }) => scoreName(col, ["total", "count", "sum", "quantity", "amount", "revenue", "sales"])) || numericCandidates[0];

  const categoryCandidates = columns
    .map((col, idx) => ({ col, idx }))
    .filter(({ idx }) => idx !== valueCandidate.idx)
    .filter(({ col, idx }) => !isIdColumn(col) && rows.some((row) => typeof row[idx] === "string" && String(row[idx]).trim() !== ""));
  if (!categoryCandidates.length) return null;

  const lineCategory = categoryCandidates.find(({ col }) => scoreName(col, ["month", "date", "year", "created", "dispensed", "ordered"]));
  const barCategory = categoryCandidates.find(({ col }) => scoreName(col, ["name", "drug", "patient", "supplier", "status", "department"]));
  const categoryCandidate = chartHint === "line" ? (lineCategory || barCategory || categoryCandidates[0]) : (barCategory || lineCategory || categoryCandidates[0]);

  const grouped = {};
  rows.forEach((row) => {
    const keyRaw = row[categoryCandidate.idx];
    const key = String(keyRaw ?? "Unknown");
    const value = Number(row[valueCandidate.idx] || 0);
    if (Number.isNaN(value)) return;
    grouped[key] = (grouped[key] || 0) + value;
  });

  const sorted = Object.entries(grouped)
    .sort((a, b) => b[1] - a[1])
    .slice(0, rows.length > 50 ? 20 : 15)
    .map(([name, value]) => ({ name: name.length > 15 ? `${name.slice(0, 15)}...` : name, value }));

  return {
    labelColumn: categoryCandidate.col,
    valueColumn: valueCandidate.col,
    chartData: sorted,
  };
}

function ChartsPanel({ columns, rows, chartHint = "auto" }) {
  if (chartHint === "none") return null;
  if (!rows || rows.length === 0 || !columns || columns.length === 0) return null;
  if (!isChartWorthwhile(columns, rows)) return null;
  const parsed = buildChartData(columns, rows, chartHint);
  if (!parsed) return null;
  const { labelColumn, valueColumn, chartData } = parsed;
  const showBar = chartHint !== "line";
  const showLine = chartHint !== "bar";
  const columnTemplate = showBar && showLine ? "1fr 1fr" : "1fr";

  return (
    <div style={{ display: "grid", gap: 12, gridTemplateColumns: columnTemplate, marginTop: 12 }}>
      {showBar && <div style={{ background: "#fff", border: "1px solid #d1d5db", borderRadius: 8, padding: 12 }}>
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
      </div>}

      {showLine && <div style={{ background: "#fff", border: "1px solid #d1d5db", borderRadius: 8, padding: 12 }}>
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
      </div>}
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
  const [showSql, setShowSql] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState("");

  const previewRows = useMemo(() => (result?.rows || []), [result]);

  async function runQuery() {
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    setSearched(true);
    setReport(null);
    setShowSql(false);
    setFeedbackMsg("");

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

  async function markResultWrong() {
    if (!question.trim()) return;
    setFeedbackMsg("");
    try {
      const res = await api.aiInvalidateRagQuery(question.trim());
      setFeedbackMsg(res?.removed ? "Removed from AI cache. Next run will regenerate." : "No cache entry found for this question.");
    } catch (err) {
      setFeedbackMsg(err.message || "Failed to update cache feedback.");
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
          {result?.cached && <span className="badge good">Cached (RAG)</span>}
          {result && <span className="badge medium">{result.count} rows</span>}
          {result && <button className="secondary-btn" onClick={() => setShowSql((prev) => !prev)}>{showSql ? "Hide SQL Query" : "Show SQL Query"}</button>}
          {result && <button className="secondary-btn" onClick={generateDownloadableReport} disabled={loading}>{loading ? "Preparing..." : "Prepare Download"}</button>}
          {result && <button className="secondary-btn" onClick={markResultWrong}>Wrong Result</button>}
        </div>
      </div>

      {error && <div className="error-msg" style={{ marginTop: 12 }}>⚠️ {error}</div>}
      {feedbackMsg && <div className="error-msg" style={{ marginTop: 12 }}>{feedbackMsg}</div>}

      {loading && <p style={{ marginTop: 12, color: "#64748b" }}>Searching database...</p>}

      {result && (
        <>
          <ChartsPanel columns={result.columns} rows={result.rows} chartHint={result.chart_hint || "auto"} />
          {result.warning && <div style={{ marginTop: 10, color: "#9a3412", fontWeight: 600 }}>{result.warning}</div>}

          {showSql && (
            <div style={{ marginTop: 12, background: "#111827", color: "#e5e7eb", padding: 12, borderRadius: 8, fontFamily: "monospace", fontSize: 12 }}>
              <div style={{ color: "#86efac", marginBottom: 6, fontSize: 11 }}>Generated SQL</div>
              <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{result.sql}</pre>
            </div>
          )}

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
