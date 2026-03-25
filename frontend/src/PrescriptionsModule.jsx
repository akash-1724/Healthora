import React, { useEffect, useState } from "react";
import { api } from "./api";
import Modal from "./Modal";

export default function PrescriptionsModule({ patients, drugs, hasPermission }) {
    const [prescriptions, setPrescriptions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [search, setSearch] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [form, setForm] = useState({ patient_id: "", diagnosis: "", notes: "", items: [{ drug_id: "", dosage: "", duration: "", quantity_prescribed: 1 }] });
    const canViewPrescriptions = hasPermission("view_prescriptions");
    const canCreatePrescription = hasPermission("add_prescriptions") && hasPermission("view_patients") && hasPermission("view_drugs");

    async function load() {
        if (!canViewPrescriptions) {
            setPrescriptions([]);
            setLoading(false);
            return;
        }
        setLoading(true);
        try { setPrescriptions(await api.getPrescriptions()); }
        catch (err) { setError(err.message); }
        finally { setLoading(false); }
    }

    useEffect(() => { load(); }, [canViewPrescriptions]);

    const filtered = prescriptions.filter((rx) => {
        const q = search.trim().toLowerCase();
        return !q || rx.patient_name.toLowerCase().includes(q) || rx.doctor_name.toLowerCase().includes(q);
    });

    function addItem() {
        setForm(p => ({ ...p, items: [...p.items, { drug_id: "", dosage: "", duration: "", quantity_prescribed: 1 }] }));
    }
    function removeItem(idx) {
        setForm(p => ({ ...p, items: p.items.filter((_, i) => i !== idx) }));
    }
    function updateItem(idx, field, value) {
        setForm(p => ({ ...p, items: p.items.map((item, i) => i === idx ? { ...item, [field]: value } : item) }));
    }

    async function createPrescription(e) {
        e.preventDefault();
        if (!form.patient_id) { setError("Select a patient"); return; }
        if (form.items.some((item) => !item.drug_id)) { setError("All items must have a drug selected"); return; }
        try {
            await api.createPrescription({
                patient_id: Number(form.patient_id),
                diagnosis: form.diagnosis || null,
                notes: form.notes || null,
                items: form.items.map((item) => ({
                    drug_id: Number(item.drug_id),
                    dosage: item.dosage || null,
                    duration: item.duration || null,
                    quantity_prescribed: Number(item.quantity_prescribed) || 1,
                })),
            });
            setShowModal(false);
            setForm({ patient_id: "", diagnosis: "", notes: "", items: [{ drug_id: "", dosage: "", duration: "", quantity_prescribed: 1 }] });
            setError("");
            await load();
        } catch (err) { setError(err.message); }
    }

    const statusBadge = { open: "good", dispensed: "medium", cancelled: "high" };

    return (
        <div className="section">
            <div className="section-header">
                <h3>Prescriptions</h3>
                {canCreatePrescription && (
                    <button className="primary-btn" onClick={() => { setError(""); setShowModal(true); }}>New Prescription</button>
                )}
            </div>
            {error && <p className="error">{error}</p>}
            <div style={{ margin: "10px 0" }}>
                <input className="input" style={{ maxWidth: 360, marginBottom: 0 }} placeholder="Search patient or doctor…" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            {loading ? <p>Loading…</p> : (
                <div className="table-wrap">
                    <table>
                        <thead><tr><th>ID</th><th>Patient</th><th>Doctor</th><th>Diagnosis</th><th>Status</th><th>Date</th></tr></thead>
                        <tbody>
                            {filtered.map((rx) => (
                                <tr key={rx.prescription_id}>
                                    <td>#{rx.prescription_id}</td>
                                    <td>{rx.patient_name}</td>
                                    <td>{rx.doctor_name}</td>
                                    <td>{rx.diagnosis || "—"}</td>
                                    <td><span className={`badge ${statusBadge[rx.status] || "good"}`}>{rx.status}</span></td>
                                    <td>{String(rx.created_at).slice(0, 10)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <Modal open={showModal} onClose={() => setShowModal(false)} title="New Prescription">
                <form onSubmit={createPrescription}>
                    <label>Patient *</label>
                    <select className="input" value={form.patient_id} onChange={(e) => setForm(p => ({ ...p, patient_id: e.target.value }))} required>
                        <option value="">Select patient…</option>
                        {patients.map((p) => <option key={p.patient_id} value={p.patient_id}>{p.name} (#{p.patient_id})</option>)}
                    </select>
                    <label>Diagnosis</label>
                    <input className="input" value={form.diagnosis} onChange={(e) => setForm(p => ({ ...p, diagnosis: e.target.value }))} />
                    <label>Notes</label>
                    <textarea className="input" value={form.notes} onChange={(e) => setForm(p => ({ ...p, notes: e.target.value }))} rows={2} />
                    <hr />
                    <strong>Prescribed Drugs</strong>
                    {form.items.map((item, idx) => (
                        <div key={idx} style={{ border: "1px solid #ccc", padding: 8, marginTop: 8 }}>
                            <label>Drug *</label>
                            <select className="input" value={item.drug_id} onChange={(e) => updateItem(idx, "drug_id", e.target.value)} required>
                                <option value="">Select drug…</option>
                                {drugs.filter((d) => d.is_active).map((d) => <option key={d.drug_id} value={d.drug_id}>{d.drug_name} {d.strength || ""}</option>)}
                            </select>
                            <label>Dosage</label>
                            <input className="input" value={item.dosage} onChange={(e) => updateItem(idx, "dosage", e.target.value)} placeholder="e.g. 1–0–1" />
                            <label>Duration</label>
                            <input className="input" value={item.duration} onChange={(e) => updateItem(idx, "duration", e.target.value)} placeholder="e.g. 5 days" />
                            <label>Qty Prescribed</label>
                            <input className="input" type="number" min="1" value={item.quantity_prescribed} onChange={(e) => updateItem(idx, "quantity_prescribed", e.target.value)} />
                            {form.items.length > 1 && <button type="button" className="danger-btn compact" onClick={() => removeItem(idx)}>Remove</button>}
                        </div>
                    ))}
                    <button type="button" className="secondary-btn compact" onClick={addItem} style={{ marginTop: 8 }}>+ Add Drug</button>
                    {error && <p className="error">{error}</p>}
                    <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                        <button className="primary-btn" type="submit">Create Prescription</button>
                        <button className="secondary-btn" type="button" onClick={() => setShowModal(false)}>Cancel</button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}
