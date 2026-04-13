import re


def _extract_top_n(query: str, default: int = 10) -> int:
    match = re.search(r"\btop\s+(\d+)\b", (query or "").lower())
    if not match:
        return default
    try:
        value = int(match.group(1))
    except Exception:
        return default
    return max(1, min(value, 200))


def route_query_template(
    question: str, schema: dict, current_user_id: int | None = None
) -> dict | None:
    q = (question or "").strip().lower()
    tables = set(schema.keys())

    if re.search(r"\b(drop|delete|update|insert|alter|truncate|grant|revoke)\b", q):
        if "users" in tables:
            return {
                "intent": "safety_read_only",
                "sql": "SELECT * FROM users",
                "path": ["users"],
            }
        if "User" in tables:
            return {
                "intent": "safety_read_only",
                "sql": 'SELECT * FROM "User"',
                "path": ["User"],
            }

    if "total patients count" in q and "patients" in tables:
        return {
            "intent": "patients_count",
            "sql": "SELECT COUNT(*) AS total_patients FROM patients",
            "path": ["patients"],
        }

    if "notifications" in q and "current user" in q and current_user_id is not None:
        return {
            "intent": "current_user_notifications",
            "sql": (
                "SELECT notification_id, title, message, is_read, created_at "
                "FROM notifications "
                f"WHERE recipient_user_id = {int(current_user_id)} "
                "ORDER BY created_at DESC"
            ),
            "path": ["notifications"],
        }

    if "pending" in q and "prescription" in q and "prescriptions" in tables:
        return {
            "intent": "pending_prescriptions",
            "sql": (
                "SELECT * FROM prescriptions "
                "WHERE LOWER(status) IN ('pending', 'open') "
                "ORDER BY created_at DESC"
            ),
            "path": ["prescriptions"],
        }

    if "count prescriptions by status" in q and "prescriptions" in tables:
        return {
            "intent": "prescriptions_by_status",
            "sql": (
                "SELECT status, COUNT(prescription_id) AS total_prescriptions "
                "FROM prescriptions "
                "GROUP BY status "
                "ORDER BY total_prescriptions DESC"
            ),
            "path": ["prescriptions"],
        }

    if (
        "suppliers" in q
        and "purchase order" in q
        and "suppliers" in tables
        and "purchase_orders" in tables
    ):
        return {
            "intent": "suppliers_with_orders",
            "sql": (
                "SELECT s.supplier_id, s.name, s.contact_person, s.phone, s.email, COUNT(po.po_id) AS purchase_orders "
                "FROM suppliers s "
                "JOIN purchase_orders po ON po.supplier_id = s.supplier_id "
                "GROUP BY s.supplier_id, s.name, s.contact_person, s.phone, s.email "
                "ORDER BY purchase_orders DESC"
            ),
            "path": ["suppliers", "purchase_orders"],
        }

    if "monthly dispensing trend" in q and "dispensing_records" in tables:
        if "2024" in q:
            return {
                "intent": "monthly_dispensing_2024",
                "sql": (
                    "SELECT EXTRACT(MONTH FROM dispensed_at) AS month, "
                    "SUM(quantity_dispensed) AS total_quantity_dispensed "
                    "FROM dispensing_records "
                    "WHERE EXTRACT(YEAR FROM dispensed_at) = 2024 "
                    "GROUP BY EXTRACT(MONTH FROM dispensed_at) "
                    "ORDER BY month"
                ),
                "path": ["dispensing_records"],
            }
        return {
            "intent": "monthly_dispensing",
            "sql": (
                "SELECT EXTRACT(YEAR FROM dispensed_at) AS year, EXTRACT(MONTH FROM dispensed_at) AS month, "
                "SUM(quantity_dispensed) AS total_quantity_dispensed "
                "FROM dispensing_records "
                "GROUP BY EXTRACT(YEAR FROM dispensed_at), EXTRACT(MONTH FROM dispensed_at) "
                "ORDER BY year, month"
            ),
            "path": ["dispensing_records"],
        }

    if (
        "total revenue by month" in q
        and "dispensing_records" in tables
        and "drug_batches" in tables
    ):
        return {
            "intent": "revenue_by_month",
            "sql": (
                "SELECT EXTRACT(YEAR FROM dr.dispensed_at) AS year, EXTRACT(MONTH FROM dr.dispensed_at) AS month, "
                "SUM(db.selling_price * dr.quantity_dispensed) AS total_revenue "
                "FROM dispensing_records dr "
                "JOIN drug_batches db ON db.batch_id = dr.batch_id "
                "GROUP BY EXTRACT(YEAR FROM dr.dispensed_at), EXTRACT(MONTH FROM dr.dispensed_at) "
                "ORDER BY year, month"
            ),
            "path": ["dispensing_records", "drug_batches"],
        }

    if (
        "top" in q
        and "drugs" in q
        and "prescription" in q
        and "prescription_items" in tables
        and "drugs" in tables
    ):
        top_n = _extract_top_n(q, 10)
        return {
            "intent": "top_drugs_by_prescriptions",
            "sql": (
                "SELECT d.drug_name, COUNT(pi.item_id) AS total_prescriptions "
                "FROM prescription_items pi "
                "JOIN drugs d ON d.drug_id = pi.drug_id "
                "GROUP BY d.drug_id, d.drug_name "
                "ORDER BY total_prescriptions DESC "
                f"LIMIT {top_n}"
            ),
            "path": ["prescription_items", "drugs"],
        }

    if (
        "doctor" in q
        and "department" in q
        and "doctor" in tables
        and "department" in tables
    ):
        return {
            "intent": "doctors_per_department",
            "sql": (
                "SELECT dep.name AS department, doc.name AS doctor_name "
                "FROM doctor doc "
                "LEFT JOIN department dep ON dep.department_id = doc.department_id "
                "WHERE doc.name IS NOT NULL "
                "ORDER BY dep.name, doc.name"
            ),
            "path": ["doctor", "department"],
        }

    if (
        "encounter" in q
        and "department" in q
        and "encounter" in tables
        and "department" in tables
    ):
        return {
            "intent": "encounters_per_department",
            "sql": (
                "SELECT dep.name AS department, COUNT(*) AS encounter_count "
                "FROM encounter e "
                "JOIN department dep ON dep.department_id = e.department_id "
                "GROUP BY dep.name "
                "ORDER BY encounter_count DESC"
            ),
            "path": ["encounter", "department"],
        }

    if (
        "most sold medicine" in q
        and "department" in q
        and all(
            table in tables
            for table in [
                "dispense_item",
                "dispense",
                "prescription",
                "encounter",
                "department",
                "drug_batch",
                "drug",
            ]
        )
    ):
        return {
            "intent": "top_medicine_per_department",
            "sql": (
                "WITH sales AS ("
                " SELECT dep.name AS department, d.drug_name AS medicine, SUM(di.quantity_dispensed) AS total_qty"
                " FROM dispense_item di"
                " JOIN dispense ds ON ds.dispense_id = di.dispense_id"
                " JOIN prescription p ON p.prescription_id = ds.prescription_id"
                " JOIN encounter e ON e.encounter_id = p.encounter_id"
                " JOIN department dep ON dep.department_id = e.department_id"
                " JOIN drug_batch db ON db.batch_id = di.batch_id"
                " JOIN drug d ON d.drug_id = db.drug_id"
                " GROUP BY dep.name, d.drug_name"
                "), ranked AS ("
                " SELECT department, medicine, total_qty, ROW_NUMBER() OVER (PARTITION BY department ORDER BY total_qty DESC) AS rn"
                " FROM sales"
                ")"
                " SELECT department, medicine AS most_sold_medicine, total_qty AS total_quantity_sold"
                " FROM ranked"
                " WHERE rn = 1"
                " ORDER BY department"
            ),
            "path": [
                "dispense_item",
                "dispense",
                "prescription",
                "encounter",
                "department",
                "drug_batch",
                "drug",
            ],
        }

    return None
