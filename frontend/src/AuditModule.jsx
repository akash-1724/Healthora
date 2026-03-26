import React, { useEffect, useState } from "react";
import { api } from "./api";

export default function AuditModule() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [actionFilter, setActionFilter] = useState("");

    const ACTION_OPTIONS = [
        "", "create_user", "add_drug", "add_batch", "dispense_drug",
        "create_prescription", "cancel_prescription",
        "create_supplier", "update_supplier", "deactivate_supplier",
        "create_purchase_order", "po_status_received", "po_status_cancelled",
    ];

    async function load() {
        setLoading(true);
        try { setLogs(await api.getAuditLogs(actionFilter || undefined)); }
        catch (err) { setError(err.message); }
        finally { setLoading(false); }
    }

    useEffect(() => { load(); }, [actionFilter]);

    return (
        <div className="section">
            <div className="section-header">
                <h3>Audit Log</h3>
                <button className="secondary-btn compact" onClick={load}>Refresh</button>
            </div>
            <div style={{ margin: "10px 0" }}>
                <select className="input compact-input" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)} style={{ marginBottom: 0 }}>
                    {ACTION_OPTIONS.map((a) => <option key={a} value={a}>{a || "All Actions"}</option>)}
                </select>
            </div>
            {error && <p className="error">{error}</p>}
            {loading ? <p>Loading…</p> : (
                <div className="table-wrap">
                    <table>
                        <thead><tr><th>Log ID</th><th>Actor</th><th>Action</th><th>Table</th><th>Timestamp</th></tr></thead>
                        <tbody>
                            {logs.map((log) => (
                                <tr key={log.log_id}>
                                    <td>#{log.log_id}</td>
                                    <td>{log.actor_username || "System"}</td>
                                    <td><code>{log.action}</code></td>
                                    <td>{log.target_table || "—"}</td>
                                    <td>{String(log.timestamp).slice(0, 19).replace("T", " ")}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
