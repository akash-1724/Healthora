import React, { useState } from "react";
import { api } from "./api";
import Modal from "./Modal";

export default function UsersModule({ users, roles, departments, onRefresh, hasPermission }) {
    const [search, setSearch] = useState("");
    const [roleFilter, setRoleFilter] = useState("all");
    const [statusFilter, setStatusFilter] = useState("all");

    const [showAdd, setShowAdd] = useState(false);
    const [showEdit, setShowEdit] = useState(false);
    const [showReset, setShowReset] = useState(false);
    const [editTarget, setEditTarget] = useState(null);
    const [resetTarget, setResetTarget] = useState(null);

    const [addForm, setAddForm] = useState({ username: "", password: "", full_name: "", email: "", phone: "", role_id: "", department: "Pharmacy" });
    const [editForm, setEditForm] = useState({ full_name: "", email: "", phone: "", role_id: "", department: "", must_reset_password: false });
    const [newPassword, setNewPassword] = useState("");
    const [errors, setErrors] = useState({});
    const [submitting, setSubmitting] = useState(false);
    const [err, setErr] = useState("");

    const filtered = users.filter((u) => {
        const q = search.toLowerCase();
        return (
            (roleFilter === "all" || String(u.role_id) === roleFilter) &&
            (statusFilter === "all" || (statusFilter === "active") === u.is_active) &&
            (!q ||
                u.username.toLowerCase().includes(q) ||
                (u.full_name || "").toLowerCase().includes(q) ||
                (u.email || "").toLowerCase().includes(q) ||
                u.department.toLowerCase().includes(q))
        );
    });

    function validate(form) {
        const e = {};
        if (!form.username?.trim()) e.username = "Required";
        if (!form.password || form.password.length < 6) e.password = "Min 6 characters";
        if (!form.role_id) e.role_id = "Required";
        if (!form.department?.trim()) e.department = "Required";
        return e;
    }

    async function onAddSubmit(e) {
        e.preventDefault();
        const v = validate(addForm);
        if (Object.keys(v).length) { setErrors(v); return; }
        setSubmitting(true); setErr("");
        try {
            await api.createUser({ ...addForm, role_id: Number(addForm.role_id), is_active: true });
            setShowAdd(false); setAddForm({ username: "", password: "", full_name: "", email: "", phone: "", role_id: "", department: "Pharmacy" }); setErrors({});
            await onRefresh();
        } catch (ex) { setErr(ex.message); } finally { setSubmitting(false); }
    }

    async function onEditSubmit(e) {
        e.preventDefault(); setSubmitting(true); setErr("");
        try {
            await api.updateUser(editTarget.user_id, {
                role_id: Number(editForm.role_id),
                department: editForm.department,
                full_name: editForm.full_name || null,
                email: editForm.email || null,
                phone: editForm.phone || null,
                must_reset_password: Boolean(editForm.must_reset_password),
            });
            setShowEdit(false); await onRefresh();
        } catch (ex) { setErr(ex.message); } finally { setSubmitting(false); }
    }

    async function onResetSubmit(e) {
        e.preventDefault();
        if (newPassword.length < 6) { setErr("Password must be at least 6 characters"); return; }
        setSubmitting(true); setErr("");
        try { await api.resetUserPassword(resetTarget.user_id, newPassword); setShowReset(false); setNewPassword(""); }
        catch (ex) { setErr(ex.message); } finally { setSubmitting(false); }
    }

    async function deactivate(u) {
        if (!confirm(`Deactivate "${u.username}"?`)) return;
        try { await api.deactivateUser(u.user_id); await onRefresh(); } catch (ex) { setErr(ex.message); }
    }
    async function del(u) {
        if (!confirm(`Permanently delete "${u.username}"? This cannot be undone.`)) return;
        try { await api.deleteUser(u.user_id); await onRefresh(); } catch (ex) { setErr(ex.message); }
    }

    return (
        <div className="section" style={{ margin: 28 }}>
            <div className="section-header">
                <h3>👥 User Management</h3>
                {hasPermission("manage_users") && <button className="primary-btn" onClick={() => { setErrors({}); setErr(""); setShowAdd(true); }}>+ Add User</button>}
            </div>

            {/* Filters */}
            <div className="inline-controls">
                <input className="input compact-input search-input" placeholder="🔍 Search username or department…"
                    value={search} onChange={(e) => setSearch(e.target.value)} />
                <select className="input compact-input" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
                    <option value="all">All Roles</option>
                    {roles.map((r) => <option key={r.id} value={r.id}>{r.display_name}</option>)}
                </select>
                <select className="input compact-input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                    <option value="all">All Status</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                </select>
            </div>

            {err && <div className="error-msg" style={{ margin: "0 20px 0" }}>⚠️ {err}</div>}

            <div className="table-wrap">
                <table>
                    <thead><tr><th>Username</th><th>Name</th><th>Contact</th><th>Role</th><th>Department</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
                    <tbody>
                        {filtered.length === 0 ? (
                            <tr><td colSpan={8} style={{ textAlign: "center", padding: 32, color: "var(--text-secondary)" }}>No users match filters</td></tr>
                        ) : filtered.map((u) => (
                            <tr key={u.user_id}>
                                <td style={{ fontWeight: 600 }}>{u.username}</td>
                                <td>{u.full_name || "-"}</td>
                                <td>{u.email || u.phone || "-"}</td>
                                <td><span style={{ color: "var(--primary)", fontSize: 13 }}>{u.role_display_name}</span></td>
                                <td style={{ color: "var(--text-secondary)" }}>{u.department}</td>
                                <td><span className={`badge ${u.is_active ? "good" : "inactive"}`}>{u.is_active ? "Active" : "Inactive"}</span></td>
                                <td style={{ color: "var(--text-secondary)", fontSize: 12 }}>{String(u.created_at).slice(0, 10)}</td>
                                <td className="actions-cell">
                                    <button className="secondary-btn compact" onClick={() => {
                                        setEditTarget(u);
                                        setEditForm({
                                            role_id: String(u.role_id),
                                            department: u.department,
                                            full_name: u.full_name || "",
                                            email: u.email || "",
                                            phone: u.phone || "",
                                            must_reset_password: Boolean(u.must_reset_password),
                                        });
                                        setShowEdit(true);
                                    }}>Edit</button>
                                    <button className="secondary-btn compact" onClick={() => { setResetTarget(u); setNewPassword(""); setErr(""); setShowReset(true); }}>Reset Pwd</button>
                                    {u.is_active && <button className="secondary-btn compact" onClick={() => deactivate(u)}>Deactivate</button>}
                                    <button className="danger-btn compact" onClick={() => del(u)}>Delete</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Add User Modal */}
            <Modal open={showAdd} onClose={() => setShowAdd(false)} title="➕ Add New User">
                <form onSubmit={onAddSubmit}>
                    <div className="form-row">
                        <div>
                            <label>Username *</label>
                            <input className="input" value={addForm.username} onChange={(e) => setAddForm(p => ({ ...p, username: e.target.value }))} required />
                            {errors.username && <p className="error">{errors.username}</p>}
                        </div>
                        <div>
                            <label>Password * (min 6 chars)</label>
                            <input className="input" type="password" value={addForm.password} onChange={(e) => setAddForm(p => ({ ...p, password: e.target.value }))} required minLength={6} />
                            {errors.password && <p className="error">{errors.password}</p>}
                        </div>
                    </div>
                    <div className="form-row">
                        <div>
                            <label>Full Name</label>
                            <input className="input" value={addForm.full_name} onChange={(e) => setAddForm(p => ({ ...p, full_name: e.target.value }))} />
                        </div>
                        <div>
                            <label>Email</label>
                            <input className="input" type="email" value={addForm.email} onChange={(e) => setAddForm(p => ({ ...p, email: e.target.value }))} />
                        </div>
                    </div>
                    <div>
                        <label>Phone</label>
                        <input className="input" value={addForm.phone} onChange={(e) => setAddForm(p => ({ ...p, phone: e.target.value }))} />
                    </div>
                    <div className="form-row">
                        <div>
                            <label>Role *</label>
                            <select className="input" value={addForm.role_id} onChange={(e) => setAddForm(p => ({ ...p, role_id: e.target.value }))} required>
                                <option value="">Select role…</option>
                                {roles.map((r) => <option key={r.id} value={r.id}>{r.display_name}</option>)}
                            </select>
                            {errors.role_id && <p className="error">{errors.role_id}</p>}
                        </div>
                        <div>
                            <label>Department *</label>
                            <select className="input" value={addForm.department} onChange={(e) => setAddForm(p => ({ ...p, department: e.target.value }))} required>
                                {departments.map((d) => <option key={d}>{d}</option>)}
                            </select>
                        </div>
                    </div>
                    {err && <div className="error-msg">⚠️ {err}</div>}
                    <div className="form-actions">
                        <button className="primary-btn" type="submit" disabled={submitting}>{submitting ? "Creating…" : "Create User"}</button>
                        <button className="secondary-btn" type="button" onClick={() => setShowAdd(false)}>Cancel</button>
                    </div>
                </form>
            </Modal>

            {/* Edit Modal */}
            <Modal open={showEdit} onClose={() => setShowEdit(false)} title={`✏️ Edit: ${editTarget?.username}`}>
                <form onSubmit={onEditSubmit}>
                    <label>Full Name</label>
                    <input className="input" value={editForm.full_name} onChange={(e) => setEditForm(p => ({ ...p, full_name: e.target.value }))} />
                    <label>Email</label>
                    <input className="input" type="email" value={editForm.email} onChange={(e) => setEditForm(p => ({ ...p, email: e.target.value }))} />
                    <label>Phone</label>
                    <input className="input" value={editForm.phone} onChange={(e) => setEditForm(p => ({ ...p, phone: e.target.value }))} />
                    <label>Role</label>
                    <select className="input" value={editForm.role_id} onChange={(e) => setEditForm(p => ({ ...p, role_id: e.target.value }))}>
                        {roles.map((r) => <option key={r.id} value={r.id}>{r.display_name}</option>)}
                    </select>
                    <label>Department</label>
                    <select className="input" value={editForm.department} onChange={(e) => setEditForm(p => ({ ...p, department: e.target.value }))}>
                        {departments.map((d) => <option key={d}>{d}</option>)}
                    </select>
                    <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                        <input type="checkbox" checked={Boolean(editForm.must_reset_password)} onChange={(e) => setEditForm(p => ({ ...p, must_reset_password: e.target.checked }))} />
                        Require password reset on next login
                    </label>
                    {err && <div className="error-msg">⚠️ {err}</div>}
                    <div className="form-actions">
                        <button className="primary-btn" type="submit" disabled={submitting}>{submitting ? "Saving…" : "Save Changes"}</button>
                        <button className="secondary-btn" type="button" onClick={() => setShowEdit(false)}>Cancel</button>
                    </div>
                </form>
            </Modal>

            {/* Reset Password Modal */}
            <Modal open={showReset} onClose={() => setShowReset(false)} title={`🔑 Reset Password: ${resetTarget?.username}`}>
                <form onSubmit={onResetSubmit}>
                    <label>New Password * (min 6 characters)</label>
                    <input className="input" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={6} placeholder="Enter new password…" />
                    {err && <div className="error-msg">⚠️ {err}</div>}
                    <div className="form-actions">
                        <button className="primary-btn" type="submit" disabled={submitting}>{submitting ? "Setting…" : "Set Password"}</button>
                        <button className="secondary-btn" type="button" onClick={() => setShowReset(false)}>Cancel</button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}
