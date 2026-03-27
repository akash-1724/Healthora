import React, { useEffect, useMemo, useState } from "react";
import { api } from "./api";

export default function ReorderRecommendationModule() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [forecastDays, setForecastDays] = useState(30);

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

  const whole = (value) => Math.round(Number(value) || 0);
  const forecastTotalKey = useMemo(() => {
    if (forecastDays === 60) return "next_60_day_forecast_total";
    if (forecastDays === 90) return "next_90_day_forecast_total";
    return "next_30_day_forecast_total";
  }, [forecastDays]);
  const reorderQtyKey = useMemo(() => {
    if (forecastDays === 60) return "recommended_reorder_qty_60";
    if (forecastDays === 90) return "recommended_reorder_qty_90";
    return "recommended_reorder_qty_30";
  }, [forecastDays]);
  const topMedicines = useMemo(() => {
    const list = [...(data?.medicines || [])];
    list.sort((a, b) => whole(b[reorderQtyKey]) - whole(a[reorderQtyKey]));
    return list.slice(0, 20);
  }, [data, reorderQtyKey]);

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
          </div>

          <div className="section" style={{ marginTop: 10 }}>
            <div className="section-header">
              <h3>Top Reorder Suggestions</h3>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  className={`secondary-btn compact ${forecastDays === 30 ? "active" : ""}`}
                  onClick={() => setForecastDays(30)}
                  style={forecastDays === 30 ? { fontWeight: 700 } : undefined}
                >
                  30 Days
                </button>
                <button
                  className={`secondary-btn compact ${forecastDays === 60 ? "active" : ""}`}
                  onClick={() => setForecastDays(60)}
                  style={forecastDays === 60 ? { fontWeight: 700 } : undefined}
                >
                  60 Days
                </button>
                <button
                  className={`secondary-btn compact ${forecastDays === 90 ? "active" : ""}`}
                  onClick={() => setForecastDays(90)}
                  style={forecastDays === 90 ? { fontWeight: 700 } : undefined}
                >
                  90 Days
                </button>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Medicine</th><th>Current Stock</th><th>Last 30d Used</th><th>Average Daily Usage</th><th>7-Day Avg Forecast</th><th>{forecastDays}-Day Forecast</th><th>Movement</th><th>Recommended Reorder</th></tr></thead>
                <tbody>
                  {topMedicines.map((m) => {
                    const next7 = m.next_7_day_forecast || [];
                    const avg7 = next7.length ? (next7.reduce((acc, d) => acc + (d.predicted_usage || 0), 0) / next7.length) : 0;
                    return (
                      <tr key={m.drug_id}>
                      <td>{m.drug_name}</td>
                      <td>{m.current_stock}</td>
                      <td>{whole(m.last_30_day_usage)}</td>
                      <td>{whole(m.average_daily_usage)}</td>
                      <td>{whole(avg7)}</td>
                      <td>{whole(m[forecastTotalKey])}</td>
                      <td>{m.movement_status}</td>
                      <td style={{ fontWeight: 700 }}>{whole(m[reorderQtyKey])}</td>
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
