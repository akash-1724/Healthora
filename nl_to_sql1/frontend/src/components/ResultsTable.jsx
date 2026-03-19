export default function ResultsTable({ columns, rows, count, sql }) {
  if (!rows || rows.length === 0) return null;

  return (
    <div style={{ padding: "24px" }}>
      {/* SQL query shown */}
      <div style={{
        background: "#1e1e2e", color: "#cdd6f4", padding: "16px",
        borderRadius: "8px", marginBottom: "16px", fontFamily: "monospace", fontSize: "13px"
      }}>
        <div style={{ color: "#a6e3a1", marginBottom: "6px", fontSize: "11px" }}>Generated SQL:</div>
        <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>{sql}</pre>
      </div>

      {/* Row count */}
      <div style={{ marginBottom: "12px", fontSize: "14px", color: "#555" }}>
        <strong>{count}</strong> rows returned
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto", borderRadius: "8px", border: "1px solid #e0e0e0" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ background: "#f5f5f5" }}>
              {columns.map(col => (
                <th key={col} style={{
                  padding: "12px 16px", textAlign: "left", fontWeight: 600,
                  borderBottom: "2px solid #e0e0e0", whiteSpace: "nowrap"
                }}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} style={{ background: i % 2 === 0 ? "#fff" : "#fafafa" }}>
                {row.map((cell, j) => (
                  <td key={j} style={{
                    padding: "10px 16px", borderBottom: "1px solid #e0e0e0"
                  }}>
                    {cell === null ? <span style={{ color: "#aaa" }}>NULL</span> : String(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}