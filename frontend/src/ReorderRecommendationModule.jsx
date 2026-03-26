import React, { useEffect, useMemo, useState } from "react";
import { api } from "./api";

function RiskBadge({ risk }) {
  const cls = risk === "high" ? "high" : risk === "medium" ? "medium" : "good";
  const text = risk === "high" ? "High Risk" : risk === "medium" ? "Medium Risk" : "Low Risk";
  return <span className={`badge ${cls}`}>{text}</span>;
}

export default function ReorderRecommendationModule() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await api.getReorderRecommendations());
    } catch (err) {
      setError(err.message || "Failed to load reorder recommendation");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const topForecast = useMemo(() => {
    const meds = data?.medicines || [];
    return [...meds].sort((a, b) => (b.average_daily_usage || 0) - (a.average_daily_usage || 0)).slice(0, 10);
  }, [data]);

  return (
    <div className="section" style={{ margin: 24 }}>
      <div className="section-header">
        <h3>Reorder Recommendation Engine</h3>
        <button className="secondary-btn compact" onClick={load}>Refresh</button>
      </div>

      {error && <div className="error-msg">{error}</div>}
      {loading ? <p>Loading...</p> : (
        <>
          <div style={{ marginBottom: 8, color: "#334155", fontWeight: 600 }}>
            Analysis Date: {data?.as_of_date || "-"}
          </div>

          <div className="cards" style={{ marginBottom: 12 }}>
            <div className="card"><h3>Total Medicines</h3><div className="card-value cyan">{data?.summary?.total_medicines ?? 0}</div></div>
            <div className="card"><h3>Raw Events (120d)</h3><div className="card-value amber">{data?.summary?.raw_events_window ?? 0}</div></div>
            <div className="card"><h3>Reorder Alerts</h3><div className="card-value red">{data?.summary?.reorder_alert_count ?? 0}</div></div>
            <div className="card"><h3>Expiry Alerts</h3><div className="card-value purple">{data?.summary?.expiry_alert_count ?? 0}</div></div>
          </div>

          <div className="section" style={{ marginTop: 10 }}>
            <div className="section-header"><h3>8-Stage Pipeline Status</h3></div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Step</th><th>Stage</th><th>Status</th><th>Metrics</th></tr></thead>
                <tbody>
                  {(data?.stages || []).map((stage) => (
                    <tr key={stage.step}>
                      <td>{stage.step}</td>
                      <td>{stage.name}</td>
                      <td><span className={`badge ${stage.status === "completed" ? "good" : "medium"}`}>{stage.status}</span></td>
                      <td>{Object.entries(stage.metrics || {}).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" | ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="section" style={{ marginTop: 10 }}>
            <div className="section-header"><h3>Top Reorder Suggestions</h3></div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Medicine</th><th>Supplier</th><th>Current Stock</th><th>Last 30d Used</th><th>Next 30d Forecast</th><th>Movement</th><th>Recommended Reorder</th></tr></thead>
                <tbody>
                  {(data?.medicines || []).slice(0, 20).map((m) => (
                    <tr key={m.drug_id}>
                      <td>{m.drug_name}</td>
                      <td>{m.suggested_supplier || "-"}</td>
                      <td>{m.current_stock}</td>
                      <td>{m.last_30_day_usage}</td>
                      <td>{m.next_30_day_forecast_total}</td>
                      <td>{m.movement_status}</td>
                      <td style={{ fontWeight: 700 }}>{m.recommended_reorder_qty}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="section" style={{ marginTop: 10 }}>
            <div className="section-header"><h3>Expiry Risk Alerts</h3></div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Medicine</th><th>Batch</th><th>Qty</th><th>Days To Expiry</th><th>Risk Score</th><th>Risk</th></tr></thead>
                <tbody>
                  {(data?.expiry_risk_alerts || []).length === 0 ? (
                    <tr><td colSpan={6} style={{ textAlign: "center", padding: 20 }}>No risk alerts</td></tr>
                  ) : (data?.expiry_risk_alerts || []).map((r) => (
                    <tr key={`${r.batch_id}-${r.drug_id}`}>
                      <td>{r.drug_name}</td>
                      <td>{r.batch_no}</td>
                      <td>{r.quantity_available}</td>
                      <td>{r.days_to_expiry}</td>
                      <td>{r.expiry_risk_score}</td>
                      <td><RiskBadge risk={r.risk} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="section" style={{ marginTop: 10 }}>
            <div className="section-header"><h3>Usage Ranking Snapshot</h3></div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Medicine</th><th>Average Daily Usage</th><th>Trend</th><th>Seasonality</th><th>MAPE</th><th>7-Day Avg Forecast</th></tr></thead>
                <tbody>
                  {topForecast.map((m) => {
                    const next7 = m.next_7_day_forecast || [];
                    const avg7 = next7.length ? (next7.reduce((acc, d) => acc + (d.predicted_usage || 0), 0) / next7.length) : 0;
                    return (
                      <tr key={`f-${m.drug_id}`}>
                        <td>{m.drug_name}</td>
                        <td>{m.average_daily_usage}</td>
                        <td>{m.trend_type}</td>
                        <td>{m.seasonality_strength}</td>
                        <td>{m.mape_estimate}%</td>
                        <td>{avg7.toFixed(2)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
