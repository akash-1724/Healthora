import React, { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import Modal from "./Modal";

export default function InventoryModule({ drugs, inventoryRows, hasPermission, onRefresh, suppliers, mode = "inventory" }) {
    const requiredBulkColumns = [
        "drug_name",
        "batch_no",
        "expiry_date",
        "purchase_price",
        "selling_price",
        "quantity_available",
    ];

    const availableTabs = useMemo(() => {
        if (mode === "drugs") return ["drugs", "batches"];
        return ["batches", "stock"];
    }, [mode]);

    const [tab, setTab] = useState(mode === "drugs" ? "drugs" : "batches");
    const [search, setSearch] = useState("");

    const [showEditDrugModal, setShowEditDrugModal] = useState(false);
    const [editDrugTarget, setEditDrugTarget] = useState(null);
    const [editDrugForm, setEditDrugForm] = useState({});

    // Batch form
    const [showUpdateQtyModal, setShowUpdateQtyModal] = useState(false);
    const [updateQtyTarget, setUpdateQtyTarget] = useState(null);
    const [newQty, setNewQty] = useState("");
    const [selectedCsvFile, setSelectedCsvFile] = useState(null);
    const [previewHeaders, setPreviewHeaders] = useState([]);
    const [previewRows, setPreviewRows] = useState([]);
    const [isUploadingCsv, setIsUploadingCsv] = useState(false);

    const [batchDrugFilter, setBatchDrugFilter] = useState("all");
    const [batchRiskFilter, setBatchRiskFilter] = useState("all");
    const [error, setError] = useState("");
    const [bulkResult, setBulkResult] = useState(null);

    useEffect(() => {
        setTab(mode === "drugs" ? "drugs" : "batches");
    }, [mode]);

    const now = new Date();

    function daysLeft(expiryDate) { return Math.floor((new Date(expiryDate) - now) / 86400000); }
    function riskLevel(d) { return d < 0 ? "expired" : d <= 30 ? "high" : d <= 60 ? "medium" : "low"; }

    function riskLabel(risk) {
        if (risk === "high") return "High Risk";
        if (risk === "medium") return "Medium Risk";
        if (risk === "low") return "Low Risk";
        if (risk === "expired") return "Expired";
        return risk;
    }

    const enrichedBatches = inventoryRows.map((row) => {
        const d = daysLeft(row.expiry_date);
        return { ...row, days_left: d, risk: riskLevel(d) };
    });

    const filteredBatches = enrichedBatches.filter((row) => {
        const drugOk = batchDrugFilter === "all" || String(row.drug_id) === batchDrugFilter;
        const riskOk = batchRiskFilter === "all" || row.risk === batchRiskFilter;
        const q = search.trim().toLowerCase();
        const searchOk = !q || row.drug_name.toLowerCase().includes(q) || row.batch_no.toLowerCase().includes(q);
        return drugOk && riskOk && searchOk;
    });

    const filteredDrugs = drugs.filter((d) => {
        const q = search.trim().toLowerCase();
        return !q || d.drug_name.toLowerCase().includes(q) || (d.generic_name || "").toLowerCase().includes(q);
    });

    function openEditDrug(row) {
        setEditDrugTarget(row);
        setEditDrugForm({ drug_name: row.drug_name, generic_name: row.generic_name || "", formulation: row.formulation || "", strength: row.strength || "", schedule_type: row.schedule_type || "", low_stock_threshold: row.low_stock_threshold });
        setShowEditDrugModal(true);
    }

    async function saveEditDrug(e) {
        e.preventDefault();
        try {
            await api.updateDrug(editDrugTarget.drug_id, { ...editDrugForm, low_stock_threshold: Number(editDrugForm.low_stock_threshold) });
            setShowEditDrugModal(false);
            setError("");
            await onRefresh();
        } catch (err) { setError(err.message); }
    }

    async function disableDrug(row) {
        if (!window.confirm(`Disable drug "${row.drug_name}"?`)) return;
        try { await api.disableDrug(row.drug_id); await onRefresh(); } catch (err) { setError(err.message); }
    }

    async function updateQty(e) {
        e.preventDefault();
        if (!newQty || isNaN(Number(newQty)) || Number(newQty) < 0) { setError("Enter a valid quantity"); return; }
        try {
            await api.updateInventory(updateQtyTarget.batch_id, { quantity_available: Number(newQty) });
            setShowUpdateQtyModal(false);
            setError("");
            await onRefresh();
        } catch (err) { setError(err.message); }
    }

    async function markExpired(row) {
        if (!window.confirm(`Mark batch "${row.batch_no}" as expired?`)) return;
        try { await api.markBatchExpired(row.batch_id); await onRefresh(); } catch (err) { setError(err.message); }
    }

    function parseCsvLine(line) {
        const values = [];
        let current = "";
        let inQuotes = false;

        for (let i = 0; i < line.length; i += 1) {
            const ch = line[i];
            if (ch === '"') {
                if (inQuotes && line[i + 1] === '"') {
                    current += '"';
                    i += 1;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (ch === "," && !inQuotes) {
                values.push(current.trim());
                current = "";
            } else {
                current += ch;
            }
        }
        values.push(current.trim());
        return values;
    }

    function normalizeHeader(value) {
        return value.trim().toLowerCase().replace(/\s+/g, "_");
    }

    async function onCsvSelected(e) {
        const file = e.target.files?.[0];
        if (!file) return;

        setError("");
        setBulkResult(null);
        setPreviewHeaders([]);
        setPreviewRows([]);

        try {
            if (!file.name.toLowerCase().endsWith(".csv")) {
                throw new Error("Only CSV files are supported here");
            }

            const text = await file.text();
            const lines = text.split(/\r?\n/).filter((line) => line.trim() !== "");
            if (lines.length < 2) {
                throw new Error("CSV must contain a header and at least one data row");
            }

            const headers = parseCsvLine(lines[0]).map(normalizeHeader).filter(Boolean);
            const missing = requiredBulkColumns.filter((column) => !headers.includes(column));
            if (missing.length > 0) {
                throw new Error(`Missing required columns: ${missing.join(", ")}`);
            }

            const rows = lines.slice(1).map((line) => {
                const cells = parseCsvLine(line);
                const mapped = {};
                headers.forEach((header, idx) => {
                    mapped[header] = cells[idx] || "";
                });
                return mapped;
            });

            setSelectedCsvFile(file);
            setPreviewHeaders(headers);
            setPreviewRows(rows);
        } catch (err) {
            setError(err.message);
        } finally {
            e.target.value = "";
        }
    }

    async function uploadPreviewedCsv() {
        if (!selectedCsvFile) {
            setError("Choose a CSV file first");
            return;
        }
        setError("");
        setIsUploadingCsv(true);
        try {
            const res = await api.bulkUploadBatches(selectedCsvFile);
            setBulkResult(res);
            setSelectedCsvFile(null);
            setPreviewHeaders([]);
            setPreviewRows([]);
            await onRefresh();
        } catch (err) {
            setError(err.message);
        } finally {
            setIsUploadingCsv(false);
        }
    }

    function cancelCsvSelection() {
        setSelectedCsvFile(null);
        setPreviewHeaders([]);
        setPreviewRows([]);
        setBulkResult(null);
        setError("");
    }

    const formulations = ["Tablet", "Capsule", "Syrup", "Injection", "Cream", "Drops", "Inhaler", "Patch", "Other"];
    const schedules = ["OTC", "Schedule H", "Schedule H1", "Schedule X", "Schedule G"];

    function DrugFormFields({ form, setForm }) {
        return (
            <>
                <label>Drug Name *</label>
                <input className="input" value={form.drug_name} onChange={(e) => setForm(p => ({ ...p, drug_name: e.target.value }))} required />
                <label>Generic Name</label>
                <input className="input" value={form.generic_name} onChange={(e) => setForm(p => ({ ...p, generic_name: e.target.value }))} />
                <label>Formulation</label>
                <select className="input" value={form.formulation} onChange={(e) => setForm(p => ({ ...p, formulation: e.target.value }))}>
                    {formulations.map((f) => <option key={f}>{f}</option>)}
                </select>
                <label>Strength</label>
                <input className="input" value={form.strength} onChange={(e) => setForm(p => ({ ...p, strength: e.target.value }))} placeholder="e.g. 500mg" />
                <label>Schedule Type</label>
                <select className="input" value={form.schedule_type} onChange={(e) => setForm(p => ({ ...p, schedule_type: e.target.value }))}>
                    {schedules.map((s) => <option key={s}>{s}</option>)}
                </select>
                <label>Low Stock Threshold</label>
                <input className="input" type="number" min="0" value={form.low_stock_threshold} onChange={(e) => setForm(p => ({ ...p, low_stock_threshold: e.target.value }))} />
            </>
        );
    }

    return (
        <div className="section">
            <div className="section-header">
                <h3>{mode === "drugs" ? "Drug Master" : "Inventory Operations"}</h3>
                <div className="inline-controls">
                    {availableTabs.map((t) => (
                        <button key={t} className={`secondary-btn compact ${tab === t ? "active-btn" : ""}`} onClick={() => setTab(t)}>
                            {t.charAt(0).toUpperCase() + t.slice(1)}
                        </button>
                    ))}
                </div>
            </div>
            {error && <p className="error">{error}</p>}

            {/* ── Drugs Tab ── */}
            {tab === "drugs" && (
                <>
                    <div className="inline-controls" style={{ margin: "10px 0" }}>
                        <input className="input compact-input" placeholder="Search drugs…" value={search} onChange={(e) => setSearch(e.target.value)} style={{ marginBottom: 0 }} />
                    </div>
                    <div className="table-wrap">
                        <table>
                            <thead><tr><th>Drug Name</th><th>Generic</th><th>Formulation</th><th>Strength</th><th>Schedule</th><th>Qty</th><th>Batches</th><th>Status</th><th>Actions</th></tr></thead>
                            <tbody>
                                {filteredDrugs.map((d) => (
                                    <tr key={d.drug_id}>
                                        <td>{d.drug_name}</td><td>{d.generic_name || "—"}</td><td>{d.formulation || "—"}</td>
                                        <td>{d.strength || "—"}</td><td>{d.schedule_type || "—"}</td>
                                        <td>{d.total_quantity ?? 0}</td><td>{d.active_batches ?? 0}</td>
                                        <td><span className={`badge ${d.is_active ? "good" : "high"}`}>{d.is_active ? "Active" : "Disabled"}</span></td>
                                        <td className="actions-cell">
                                            {hasPermission("add_drug") && <button className="secondary-btn compact" onClick={() => openEditDrug(d)}>Edit</button>}
                                            <button className="secondary-btn compact" onClick={() => { setTab("batches"); setBatchDrugFilter(String(d.drug_id)); }}>View Batches</button>
                                            {hasPermission("add_drug") && d.is_active && <button className="danger-btn compact" onClick={() => disableDrug(d)}>Disable</button>}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}

            {/* ── Batches Tab ── */}
            {tab === "batches" && (
                <>
                    <div className="inline-controls" style={{ margin: "10px 0" }}>
                        {hasPermission("add_batch") && (
                            <label className="secondary-btn" style={{ cursor: "pointer", marginBottom: 0 }}>
                                Select CSV
                                <input type="file" accept=".csv" onChange={onCsvSelected} style={{ display: "none" }} />
                            </label>
                        )}
                        {hasPermission("add_batch") && selectedCsvFile && (
                            <>
                                <button className="primary-btn" onClick={uploadPreviewedCsv} disabled={isUploadingCsv}>
                                    {isUploadingCsv ? "Adding Data..." : "Add Data"}
                                </button>
                                <button className="secondary-btn" onClick={cancelCsvSelection} disabled={isUploadingCsv}>
                                    Cancel
                                </button>
                            </>
                        )}
                        <select className="input compact-input" value={batchDrugFilter} onChange={(e) => setBatchDrugFilter(e.target.value)} style={{ marginBottom: 0 }}>
                            <option value="all">All Drugs</option>
                            {drugs.map((d) => <option key={d.drug_id} value={d.drug_id}>{d.drug_name}</option>)}
                        </select>
                        <select className="input compact-input" value={batchRiskFilter} onChange={(e) => setBatchRiskFilter(e.target.value)} style={{ marginBottom: 0 }}>
                            <option value="all">All Risk</option>
                            <option value="high">High Risk (&lt;30d)</option>
                            <option value="medium">Medium Risk (30–60d)</option>
                            <option value="low">Low Risk</option>
                            <option value="expired">Expired</option>
                        </select>
                        <input className="input compact-input" placeholder="Search batch/drug…" value={search} onChange={(e) => setSearch(e.target.value)} style={{ marginBottom: 0 }} />
                    </div>
                    {selectedCsvFile && previewRows.length > 0 && (
                        <div style={{ marginBottom: 10, padding: 10, border: "1px solid #cbd5e1", borderRadius: 8, background: "#fff" }}>
                            <strong>CSV Preview:</strong> {selectedCsvFile.name} ({previewRows.length} rows)
                            <div className="table-wrap" style={{ marginTop: 8 }}>
                                <table>
                                    <thead>
                                        <tr>
                                            {previewHeaders.map((h) => <th key={h}>{h}</th>)}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {previewRows.slice(0, 8).map((row, idx) => (
                                            <tr key={`${row.batch_no || "row"}-${idx}`}>
                                                {previewHeaders.map((h) => <td key={`${h}-${idx}`}>{row[h] || "—"}</td>)}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                            {previewRows.length > 8 && (
                                <div style={{ marginTop: 8, color: "#64748b", fontSize: 12 }}>Showing first 8 rows only</div>
                            )}
                        </div>
                    )}
                    {bulkResult && (
                        <div style={{ marginBottom: 10, padding: 10, border: "1px solid #cbd5e1", borderRadius: 8, background: "#f8fafc" }}>
                            <strong>Bulk Upload Result:</strong> Rows: {bulkResult.total_rows}, Added batches: {bulkResult.created_batches}, New drugs: {bulkResult.created_drugs}, New suppliers: {bulkResult.created_suppliers}, Failed: {bulkResult.failed_rows}
                            {bulkResult.errors?.length > 0 && (
                                <ul style={{ marginTop: 8, paddingLeft: 18 }}>
                                    {bulkResult.errors.slice(0, 5).map((er, idx) => <li key={idx}>Row {er.row}: {er.error}</li>)}
                                </ul>
                            )}
                        </div>
                    )}
                    <div className="table-wrap">
                        <table>
                            <thead><tr><th>Drug</th><th>Batch No</th><th>Expiry</th><th>Days Left</th><th>Qty</th><th>Buy Price</th><th>Sell Price</th><th>Supplier</th><th>Status</th><th>Actions</th></tr></thead>
                            <tbody>
                                {filteredBatches.map((row) => (
                                    <tr key={row.batch_id}>
                                        <td>{row.drug_name}</td><td>{row.batch_no}</td><td>{row.expiry_date}</td>
                                        <td>{row.days_left}</td><td>{row.quantity_available}</td>
                                        <td>₹{row.purchase_price}</td><td>₹{row.selling_price}</td>
                                        <td>{row.supplier_name || "—"}</td>
                                        <td><span className={`badge ${row.risk === "expired" ? "high" : row.risk === "high" ? "high" : row.risk === "medium" ? "medium" : "good"}`}>{riskLabel(row.risk)}</span></td>
                                        <td className="actions-cell">
                                            {hasPermission("update_inventory") && !row.is_expired && (
                                                <button className="secondary-btn compact" onClick={() => { setUpdateQtyTarget(row); setNewQty(String(row.quantity_available)); setShowUpdateQtyModal(true); }}>
                                                    Update Qty
                                                </button>
                                            )}
                                            {!row.is_expired && <button className="danger-btn compact" onClick={() => markExpired(row)}>Mark Expired</button>}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}

            {/* ── Stock View Tab ── */}
            {tab === "stock" && (
                <div className="table-wrap" style={{ marginTop: 10 }}>
                    <table>
                        <thead><tr><th>Drug Name</th><th>Total Stock</th><th>Low Stock Threshold</th><th>Status</th><th>Actions</th></tr></thead>
                        <tbody>
                            {drugs.map((drug) => {
                                const rows = inventoryRows.filter((r) => r.drug_id === drug.drug_id);
                                const total = rows.reduce((a, r) => a + r.quantity_available, 0);
                                const isLow = total < drug.low_stock_threshold;
                                return (
                                    <tr key={drug.drug_id}>
                                        <td>{drug.drug_name}</td>
                                        <td>{total}</td>
                                        <td>{drug.low_stock_threshold}</td>
                                        <td><span className={`badge ${isLow ? "high" : "good"}`}>{isLow ? "Low" : "Good"}</span></td>
                                        <td className="actions-cell">
                                            <button className="secondary-btn compact" onClick={() => { setTab("batches"); setBatchDrugFilter(String(drug.drug_id)); }}>View Batches</button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Edit Drug Modal */}
            <Modal open={showEditDrugModal} onClose={() => setShowEditDrugModal(false)} title={`Edit Drug: ${editDrugTarget?.drug_name}`}>
                <form onSubmit={saveEditDrug}>
                    <DrugFormFields form={editDrugForm} setForm={setEditDrugForm} />
                    {error && <p className="error">{error}</p>}
                    <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <button className="primary-btn" type="submit">Save Changes</button>
                        <button className="secondary-btn" type="button" onClick={() => setShowEditDrugModal(false)}>Cancel</button>
                    </div>
                </form>
            </Modal>

            {/* Update Quantity Modal */}
            <Modal open={showUpdateQtyModal} onClose={() => setShowUpdateQtyModal(false)} title={`Update Quantity: ${updateQtyTarget?.batch_no}`}>
                <form onSubmit={updateQty}>
                    <p style={{ margin: "0 0 10px" }}>Drug: <strong>{updateQtyTarget?.drug_name}</strong></p>
                    <label>New Quantity *</label>
                    <input className="input" type="number" min="0" value={newQty} onChange={(e) => setNewQty(e.target.value)} required />
                    {error && <p className="error">{error}</p>}
                    <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <button className="primary-btn" type="submit">Save</button>
                        <button className="secondary-btn" type="button" onClick={() => setShowUpdateQtyModal(false)}>Cancel</button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}
