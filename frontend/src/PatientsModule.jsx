import React, { useState } from "react";
import { api } from "./api";
import Modal from "./Modal";

export default function PatientsModule({ patients, hasPermission, onRefresh }) {
    const [search, setSearch] = useState("");
    const [showAddModal, setShowAddModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [editTarget, setEditTarget] = useState(null);
    const [error, setError] = useState("");

    const [newPatient, setNewPatient] = useState({ name: "", contact: "", gender: "", dob: "", blood_group: "", address: "" });
    const [editForm, setEditForm] = useState({});

    const filtered = patients.filter((p) => {
        const q = search.trim().toLowerCase();
        return !q || p.name.toLowerCase().includes(q) || (p.contact || "").includes(q) || String(p.patient_id).includes(q);
    });

    function validatePatient(form) {
        if (!form.name || !form.name.trim()) return "Patient name is required";
        if (form.dob) {
            const parsed = parseDobToIso(form.dob);
            if (!parsed) return "Date of Birth is invalid";
            const year = Number(parsed.slice(0, 4));
            const today = new Date().toISOString().slice(0, 10);
            if (year < 1900) return "Date of Birth year must be 1900 or later";
            if (parsed > today) return "Date of Birth cannot be in the future";
        }
        return null;
    }

    async function createPatient(e) {
        e.preventDefault();
        const err = validatePatient(newPatient);
        if (err) { setError(err); return; }
        try {
            await api.createPatient({
                name: newPatient.name.trim(),
                contact: newPatient.contact || null,
                gender: newPatient.gender || null,
                dob: parseDobToIso(newPatient.dob) || null,
                blood_group: newPatient.blood_group || null,
                address: newPatient.address || null,
            });
            setShowAddModal(false);
            setNewPatient({ name: "", contact: "", gender: "", dob: "", blood_group: "", address: "" });
            setError("");
            await onRefresh();
        } catch (err) { setError(err.message); }
    }

    function openEdit(row) {
        setEditTarget(row);
        setEditForm({
            name: row.name,
            contact: row.contact || "",
            gender: row.gender || "",
            dob: parseDobToIso(row.dob) || "",
            blood_group: row.blood_group || "",
            address: row.address || "",
        });
        setShowEditModal(true);
    }

    async function saveEdit(e) {
        e.preventDefault();
        const err = validatePatient(editForm);
        if (err) { setError(err); return; }
        try {
            await api.updatePatient(editTarget.patient_id, {
                name: editForm.name.trim(),
                contact: editForm.contact || null,
                gender: editForm.gender || null,
                dob: parseDobToIso(editForm.dob) || null,
                blood_group: editForm.blood_group || null,
                address: editForm.address || null,
            });
            setShowEditModal(false);
            setError("");
            await onRefresh();
        } catch (err) { setError(err.message); }
    }

    async function archivePatient(row) {
        if (!window.confirm(`Archive patient "${row.name}" (ID ${row.patient_id})?`)) return;
        try { await api.archivePatient(row.patient_id); await onRefresh(); } catch (err) { setError(err.message); }
    }

    const genderOptions = ["", "Male", "Female", "Other"];
    const bloodGroups = ["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
    const today = new Date().toISOString().slice(0, 10);

    function parseDobToIso(value) {
        if (!value) return "";
        const raw = String(value).trim();
        if (!raw) return "";

        const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;

        const dmy = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
        if (dmy) return `${dmy[3]}-${dmy[2]}-${dmy[1]}`;

        return "";
    }

    function PatientForm({ form, setForm, onSubmit, submitLabel }) {
        return (
            <form onSubmit={onSubmit}>
                <label>Full Name *</label>
                <input className="input" value={form.name} onChange={(e) => setForm(p => ({ ...p, name: e.target.value }))} required />
                <label>Gender</label>
                <select className="input" value={form.gender} onChange={(e) => setForm(p => ({ ...p, gender: e.target.value }))}>
                    {genderOptions.map((g) => <option key={g} value={g}>{g || "— Select —"}</option>)}
                </select>
                <label>Date of Birth</label>
                <input
                    className="input"
                    type="date"
                    value={form.dob || ""}
                    min="1900-01-01"
                    max={today}
                    onChange={(e) => setForm(p => ({ ...p, dob: e.target.value }))}
                />
                <label>Contact Number</label>
                <input className="input" type="tel" value={form.contact} onChange={(e) => setForm(p => ({ ...p, contact: e.target.value }))} placeholder="+91-XXXXX-XXXXX" />
                <label>Blood Group</label>
                <select className="input" value={form.blood_group} onChange={(e) => setForm(p => ({ ...p, blood_group: e.target.value }))}>
                    {bloodGroups.map((bg) => <option key={bg} value={bg}>{bg || "— Select —"}</option>)}
                </select>
                <label>Address</label>
                <input className="input" value={form.address} onChange={(e) => setForm(p => ({ ...p, address: e.target.value }))} />
                {error && <p className="error">{error}</p>}
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                    <button className="primary-btn" type="submit">{submitLabel}</button>
                </div>
            </form>
        );
    }

    return (
        <div className="section">
            <div className="section-header">
                <h3>Patients</h3>
                {hasPermission("add_patients") && (
                    <button className="primary-btn" onClick={() => { setError(""); setShowAddModal(true); }}>Add Patient</button>
                )}
            </div>
            <div style={{ margin: "10px 0" }}>
                <input className="input" placeholder="Search by name, contact, ID…" value={search} onChange={(e) => setSearch(e.target.value)} style={{ marginBottom: 0, maxWidth: 360 }} />
            </div>
            <div className="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th><th>Name</th><th>Gender</th><th>Contact</th><th>Blood Group</th>
                            <th>Created By</th><th>Date</th>{hasPermission("add_patients") && <th>Actions</th>}
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map((p) => (
                            <tr key={p.patient_id}>
                                <td>{p.patient_id}</td>
                                <td>{p.name}</td>
                                <td>{p.gender || "—"}</td>
                                <td>{p.contact || "—"}</td>
                                <td>{p.blood_group || "—"}</td>
                                <td>{p.created_by || "System"}</td>
                                <td>{String(p.created_at || "").slice(0, 10)}</td>
                                {hasPermission("add_patients") && (
                                    <td className="actions-cell">
                                        <button className="secondary-btn compact" onClick={() => openEdit(p)}>Edit</button>
                                        <button className="danger-btn compact" onClick={() => archivePatient(p)}>Archive</button>
                                    </td>
                                )}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <Modal open={showAddModal} onClose={() => setShowAddModal(false)} title="Register New Patient">
                <PatientForm form={newPatient} setForm={setNewPatient} onSubmit={createPatient} submitLabel="Register Patient" />
            </Modal>

            <Modal open={showEditModal} onClose={() => setShowEditModal(false)} title={`Edit Patient: ${editTarget?.name}`}>
                <PatientForm form={editForm} setForm={setEditForm} onSubmit={saveEdit} submitLabel="Save Changes" />
            </Modal>
        </div>
    );
}
