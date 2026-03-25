import React, { useEffect, useState } from "react";
import { api } from "./api";

export default function DispensingModule({ hasPermission }) {
    const [prescriptions, setPrescriptions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [dispatchingId, setDispatchingId] = useState(null);

    const canViewDispensing = hasPermission("view_dispensing") && hasPermission("view_prescriptions");
    const canDispatch = hasPermission("dispense_drugs");

    async function load() {
        if (!canViewDispensing) {
            setPrescriptions([]);
            setLoading(false);
            return;
        }
        setLoading(true);
        try {
            const all = await api.getPrescriptions();
            setPrescriptions(all.filter((rx) => rx.status === "open"));
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        load();
    }, [canViewDispensing]);

    async function dispatchPrescription(rx) {
        if (!window.confirm(`Dispatch prescription #${rx.prescription_id}?`)) return;
        setDispatchingId(rx.prescription_id);
        setError("");
        try {
            await api.dispatchPrescription(rx.prescription_id);
            await load();
        } catch (err) {
            setError(err.message);
        } finally {
            setDispatchingId(null);
        }
    }

    return (
        <div className="section">
            <div className="section-header">
                <h3>Pending Prescription Dispatch</h3>
            </div>
            {error && <p className="error">{error}</p>}
            {loading ? <p>Loading…</p> : (
                <div className="table-wrap">
                    <table>
                        <thead>
                            <tr><th>ID</th><th>Patient</th><th>Doctor</th><th>Date</th><th>Items</th><th>Action</th></tr>
                        </thead>
                        <tbody>
                            {prescriptions.length === 0 ? (
                                <tr><td colSpan={6} style={{ textAlign: "center", padding: 24 }}>No active prescriptions pending dispatch.</td></tr>
                            ) : prescriptions.map((rx) => (
                                <tr key={rx.prescription_id}>
                                    <td>#{rx.prescription_id}</td>
                                    <td>{rx.patient_name}</td>
                                    <td>{rx.doctor_name}</td>
                                    <td>{String(rx.created_at).slice(0, 10)}</td>
                                    <td>{rx.items?.length || 0}</td>
                                    <td className="actions-cell">
                                        {canDispatch && (
                                            <button
                                                className="primary-btn compact"
                                                disabled={dispatchingId === rx.prescription_id}
                                                onClick={() => dispatchPrescription(rx)}
                                            >
                                                {dispatchingId === rx.prescription_id ? "Dispatching..." : "Dispatch"}
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
