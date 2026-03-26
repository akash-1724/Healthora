import React, { useEffect, useState } from "react";
import { api } from "./api";
import Modal from "./Modal";

export default function PurchaseOrdersModule({ drugs, hasPermission }) {
    const [orders, setOrders] = useState([]);
    const [suppliers, setSuppliers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [expandedPoId, setExpandedPoId] = useState(null);
    const [form, setForm] = useState({ supplier_id: "", notes: "", items: [{ drug_id: "", quantity_ordered: 1 }] });

    async function load() {
        setLoading(true);
        try {
            const [o, s] = await Promise.all([api.getPurchaseOrders(), api.getSuppliers()]);
            setOrders(o);
            setSuppliers(s.filter((s) => s.is_active));
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    }

    useEffect(() => { load(); }, []);

    function addItem() {
        setForm(p => ({ ...p, items: [...p.items, { drug_id: "", quantity_ordered: 1 }] }));
    }
    function removeItem(idx) {
        setForm(p => ({ ...p, items: p.items.filter((_, i) => i !== idx) }));
    }
    function updateItem(idx, field, value) {
        setForm(p => ({ ...p, items: p.items.map((item, i) => i === idx ? { ...item, [field]: value } : item) }));
    }

    async function createPO(e) {
        e.preventDefault();
        if (!form.supplier_id) { setError("Select a supplier"); return; }
        if (form.items.some((i) => !i.drug_id || !i.quantity_ordered)) { setError("All items must have drug and quantity"); return; }
        try {
            await api.createPurchaseOrder({
                supplier_id: Number(form.supplier_id),
                notes: form.notes || null,
                items: form.items.map((i) => ({
                    drug_id: Number(i.drug_id),
                    quantity_ordered: Number(i.quantity_ordered),
                })),
            });
            setShowModal(false);
            setForm({ supplier_id: "", notes: "", items: [{ drug_id: "", quantity_ordered: 1 }] });
            setError("");
            await load();
        } catch (err) { setError(err.message); }
    }

    async function updateStatus(po, status) {
        const label = status === "received" ? "Mark this PO as delivered?" : "Cancel this PO?";
        if (!window.confirm(label)) return;
        try { await api.updatePOStatus(po.po_id, status); await load(); } catch (err) { setError(err.message); }
    }

    const statusBadge = { pending: "medium", ordered: "medium", received: "good", delivered: "good", cancelled: "high" };

    function uiStatus(status) {
        if (status === "pending") return "ordered";
        if (status === "received") return "delivered";
        return status;
    }

    function canMarkDelivered(po) {
        return ["pending", "ordered"].includes((po.status || "").toLowerCase());
    }

    return (
        <div className="section">
            <div className="section-header">
                <h3>Purchase Orders</h3>
                {hasPermission("manage_inventory") && (
                    <button className="primary-btn" onClick={() => { setError(""); setShowModal(true); }}>New PO</button>
                )}
            </div>
            {error && <p className="error">{error}</p>}
            {loading ? <p>Loading…</p> : (
                <div className="table-wrap">
                    <table>
                        <thead><tr><th>PO #</th><th>Supplier</th><th>Items</th><th>Status</th><th>Date</th><th>Actions</th></tr></thead>
                        <tbody>
                            {orders.map((po) => (
                                <React.Fragment key={po.po_id}>
                                    <tr>
                                        <td>#{po.po_id}</td>
                                        <td>{po.supplier_name}</td>
                                        <td>
                                            <button className="secondary-btn compact" onClick={() => setExpandedPoId(expandedPoId === po.po_id ? null : po.po_id)}>
                                                {po.items.length} item(s)
                                            </button>
                                        </td>
                                        <td><span className={`badge ${statusBadge[po.status] || "medium"}`}>{uiStatus(po.status)}</span></td>
                                        <td>{String(po.created_at).slice(0, 10)}</td>
                                        <td className="actions-cell">
                                            {canMarkDelivered(po) && hasPermission("manage_inventory") && (
                                                <button className="primary-btn compact" onClick={() => updateStatus(po, "received")}>Mark Delivered</button>
                                            )}
                                        </td>
                                    </tr>
                                    {expandedPoId === po.po_id && (
                                        <tr>
                                            <td colSpan={6}>
                                                <div style={{ padding: "8px 10px", background: "#f8fafc", border: "1px solid #cbd5e1" }}>
                                                    <strong>Ordered Items</strong>
                                                    <div className="table-wrap" style={{ marginTop: 8 }}>
                                                        <table>
                                                            <thead><tr><th>Drug</th><th>Quantity</th></tr></thead>
                                                            <tbody>
                                                                {po.items.map((item) => (
                                                                    <tr key={item.item_id}>
                                                                        <td>{item.drug_name}</td>
                                                                        <td>{item.quantity_ordered}</td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <Modal open={showModal} onClose={() => setShowModal(false)} title="New Purchase Order">
                <form onSubmit={createPO}>
                    <label>Supplier *</label>
                    <select className="input" value={form.supplier_id} onChange={(e) => setForm(p => ({ ...p, supplier_id: e.target.value }))} required>
                        <option value="">Select supplier…</option>
                        {suppliers.map((s) => <option key={s.supplier_id} value={s.supplier_id}>{s.name}</option>)}
                    </select>
                    <label>Notes</label>
                    <textarea className="input" value={form.notes} onChange={(e) => setForm(p => ({ ...p, notes: e.target.value }))} rows={2} />
                    <hr />
                    <strong>Items</strong>
                    {form.items.map((item, idx) => (
                        <div key={idx} style={{ border: "1px solid #ccc", padding: 8, marginTop: 8 }}>
                            <label>Drug *</label>
                            <select className="input" value={item.drug_id} onChange={(e) => updateItem(idx, "drug_id", e.target.value)} required>
                                <option value="">Select drug…</option>
                                {drugs.filter((d) => d.is_active).map((d) => <option key={d.drug_id} value={d.drug_id}>{d.drug_name} {d.strength || ""}</option>)}
                            </select>
                            <label>Quantity *</label>
                            <input className="input" type="number" min="1" value={item.quantity_ordered} onChange={(e) => updateItem(idx, "quantity_ordered", e.target.value)} required />
                            {form.items.length > 1 && <button type="button" className="danger-btn compact" onClick={() => removeItem(idx)}>Remove</button>}
                        </div>
                    ))}
                    <button type="button" className="secondary-btn compact" onClick={addItem} style={{ marginTop: 8 }}>+ Add Item</button>
                    {error && <p className="error">{error}</p>}
                    <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                        <button className="primary-btn" type="submit">Create PO</button>
                        <button className="secondary-btn" type="button" onClick={() => setShowModal(false)}>Cancel</button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}
