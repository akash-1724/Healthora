import React, { useEffect, useState } from "react";
import { api } from "./api";
import Modal from "./Modal";

export default function DispensingModule({ patients, inventoryRows, hasPermission }) {
    const [records, setRecords] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [form, setForm] = useState({ patient_id: "", batch_id: "", quantity_dispensed: 1, prescription_id: "", notes: "" });
    const canViewDispensing = hasPermission("view_dispensing");
    const canDispense = hasPermission("dispense_drugs") && hasPermission("view_inventory");
    const canViewPatients = hasPermission("view_patients");

    async function load() {
        if (!canViewDispensing) {
            setRecords([]);
            setLoading(false);
            return;
        }
        setLoading(true);
        try { setRecords(await api.getDispensingRecords()); }
        catch (err) { setError(err.message); }
        finally { setLoading(false); }
    }

    useEffect(() => { load(); }, [canViewDispensing]);

    const availableBatches = inventoryRows.filter((b) => !b.is_expired && b.quantity_available > 0);

    async function dispense(e) {
        e.preventDefault();
        if (!form.patient_id) { setError("Select a patient"); return; }
        if (!form.batch_id) { setError("Select a batch"); return; }
        if (!form.quantity_dispensed || Number(form.quantity_dispensed) < 1) { setError("Quantity must be at least 1"); return; }
        try {
            await api.dispense({
                patient_id: Number(form.patient_id),
                batch_id: Number(form.batch_id),
                quantity_dispensed: Number(form.quantity_dispensed),
                prescription_id: form.prescription_id ? Number(form.prescription_id) : null,
                notes: form.notes || null,
            });
            setShowModal(false);
            setForm({ patient_id: "", batch_id: "", quantity_dispensed: 1, prescription_id: "", notes: "" });
            setError("");
            await load();
        } catch (err) { setError(err.message); }
    }

    const selectedBatch = availableBatches.find((b) => String(b.batch_id) === String(form.batch_id));

    return (
        <div className="section">
            <div className="section-header">
                <h3>Dispensing Records</h3>
                {canDispense && (
                    <button className="primary-btn" onClick={() => { setError(""); setShowModal(true); }}>Dispense Drug</button>
                )}
            </div>
            {error && <p className="error">{error}</p>}
            {loading ? <p>Loading…</p> : (
                <div className="table-wrap">
                    <table>
                        <thead>
                            <tr><th>ID</th><th>Drug</th><th>Batch</th><th>Patient ID</th><th>Qty</th><th>Dispensed By</th><th>Date & Time</th><th>Notes</th></tr>
                        </thead>
                        <tbody>
                            {records.map((r) => (
                                <tr key={r.record_id}>
                                    <td>#{r.record_id}</td>
                                    <td>{r.drug_name}</td>
                                    <td>{r.batch_no}</td>
                                    <td>{r.patient_id}</td>
                                    <td>{r.quantity_dispensed}</td>
                                    <td>{r.dispensed_by_username}</td>
                                    <td>{String(r.dispensed_at).slice(0, 19).replace("T", " ")}</td>
                                    <td>{r.notes || "—"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <Modal open={showModal} onClose={() => setShowModal(false)} title="Dispense Drug">
                <form onSubmit={dispense}>
                    <label>Patient *</label>
                    {canViewPatients ? (
                        <select className="input" value={form.patient_id} onChange={(e) => setForm(p => ({ ...p, patient_id: e.target.value }))} required>
                            <option value="">Select patient…</option>
                            {patients.map((p) => <option key={p.patient_id} value={p.patient_id}>{p.name} (#{p.patient_id})</option>)}
                        </select>
                    ) : (
                        <input
                            className="input"
                            type="number"
                            min="1"
                            value={form.patient_id}
                            onChange={(e) => setForm(p => ({ ...p, patient_id: e.target.value }))}
                            placeholder="Enter patient ID"
                            required
                        />
                    )}
                    <label>Drug Batch *</label>
                    <select className="input" value={form.batch_id} onChange={(e) => setForm(p => ({ ...p, batch_id: e.target.value }))} required>
                        <option value="">Select batch…</option>
                        {availableBatches.map((b) => (
                            <option key={b.batch_id} value={b.batch_id}>{b.drug_name} — {b.batch_no} (Qty: {b.quantity_available}, Exp: {b.expiry_date})</option>
                        ))}
                    </select>
                    {selectedBatch && (
                        <p style={{ margin: "4px 0 8px", color: "#475569", fontSize: 13 }}>
                            Available: {selectedBatch.quantity_available} units | Selling price: ₹{selectedBatch.selling_price}
                        </p>
                    )}
                    <label>Quantity to Dispense *</label>
                    <input className="input" type="number" min="1" max={selectedBatch?.quantity_available || undefined}
                        value={form.quantity_dispensed} onChange={(e) => setForm(p => ({ ...p, quantity_dispensed: e.target.value }))} required />
                    <label>Prescription ID (optional)</label>
                    <input className="input" type="number" min="1" value={form.prescription_id}
                        onChange={(e) => setForm(p => ({ ...p, prescription_id: e.target.value }))} placeholder="Link to existing prescription" />
                    <label>Notes</label>
                    <textarea className="input" value={form.notes} onChange={(e) => setForm(p => ({ ...p, notes: e.target.value }))} rows={2} />
                    {error && <p className="error">{error}</p>}
                    <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <button className="primary-btn" type="submit">Confirm Dispense</button>
                        <button className="secondary-btn" type="button" onClick={() => setShowModal(false)}>Cancel</button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}
