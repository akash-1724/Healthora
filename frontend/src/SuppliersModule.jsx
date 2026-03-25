import React, { useEffect, useState } from "react";
import { api } from "./api";
import Modal from "./Modal";

export default function SuppliersModule({ hasPermission }) {
    const [suppliers, setSuppliers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [showAddModal, setShowAddModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [editTarget, setEditTarget] = useState(null);
    const [form, setForm] = useState({ name: "", phone: "", email: "", address: "" });

    async function load() {
        setLoading(true);
        try { setSuppliers(await api.getSuppliers()); }
        catch (err) { setError(err.message); }
        finally { setLoading(false); }
    }

    useEffect(() => { load(); }, []);

    async function createSupplier(e) {
        e.preventDefault();
        if (!form.name.trim()) { setError("Supplier name is required"); return; }
        try {
            await api.createSupplier(form);
            setShowAddModal(false);
            setForm({ name: "", phone: "", email: "", address: "" });
            setError("");
            await load();
        } catch (err) { setError(err.message); }
    }

    function openEdit(s) {
        setEditTarget(s);
        setForm({ name: s.name, phone: s.phone || "", email: s.email || "", address: s.address || "" });
        setShowEditModal(true);
    }

    async function saveEdit(e) {
        e.preventDefault();
        try {
            await api.updateSupplier(editTarget.supplier_id, form);
            setShowEditModal(false);
            setError("");
            await load();
        } catch (err) { setError(err.message); }
    }

    async function deactivate(s) {
        if (!window.confirm(`Deactivate supplier "${s.name}"?`)) return;
        try { await api.deleteSupplier(s.supplier_id); await load(); } catch (err) { setError(err.message); }
    }

    function SupplierFormFields() {
        return (
            <>
                <label>Supplier Name *</label>
                <input className="input" value={form.name} onChange={(e) => setForm(p => ({ ...p, name: e.target.value }))} required />
                <label>Phone</label>
                <input className="input" type="tel" value={form.phone} onChange={(e) => setForm(p => ({ ...p, phone: e.target.value }))} />
                <label>Email</label>
                <input className="input" type="email" value={form.email} onChange={(e) => setForm(p => ({ ...p, email: e.target.value }))} />
                <label>Address</label>
                <input className="input" value={form.address} onChange={(e) => setForm(p => ({ ...p, address: e.target.value }))} />
            </>
        );
    }

    return (
        <div className="section">
            <div className="section-header">
                <h3>Suppliers</h3>
                {hasPermission("manage_suppliers") && (
                    <button className="primary-btn" onClick={() => { setError(""); setForm({ name: "", phone: "", email: "", address: "" }); setShowAddModal(true); }}>
                        Add Supplier
                    </button>
                )}
            </div>
            {error && <p className="error">{error}</p>}
            {loading ? <p>Loading…</p> : (
                <div className="table-wrap">
                    <table>
                        <thead><tr><th>Name</th><th>Phone</th><th>Email</th><th>Status</th><th>Actions</th></tr></thead>
                        <tbody>
                            {suppliers.map((s) => (
                                <tr key={s.supplier_id}>
                                    <td>{s.name}</td>
                                    <td>{s.phone || "—"}</td>
                                    <td>{s.email || "—"}</td>
                                    <td><span className={`badge ${s.is_active ? "good" : "high"}`}>{s.is_active ? "Active" : "Inactive"}</span></td>
                                    <td className="actions-cell">
                                        {hasPermission("manage_suppliers") && (
                                            <>
                                                <button className="secondary-btn compact" onClick={() => openEdit(s)}>Edit</button>
                                                {s.is_active && <button className="danger-btn compact" onClick={() => deactivate(s)}>Deactivate</button>}
                                            </>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
            <Modal open={showAddModal} onClose={() => setShowAddModal(false)} title="Add Supplier">
                <form onSubmit={createSupplier}>
                    <SupplierFormFields />
                    {error && <p className="error">{error}</p>}
                    <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <button className="primary-btn" type="submit">Add Supplier</button>
                        <button className="secondary-btn" type="button" onClick={() => setShowAddModal(false)}>Cancel</button>
                    </div>
                </form>
            </Modal>
            <Modal open={showEditModal} onClose={() => setShowEditModal(false)} title={`Edit: ${editTarget?.name}`}>
                <form onSubmit={saveEdit}>
                    <SupplierFormFields />
                    {error && <p className="error">{error}</p>}
                    <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <button className="primary-btn" type="submit">Save Changes</button>
                        <button className="secondary-btn" type="button" onClick={() => setShowEditModal(false)}>Cancel</button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}
