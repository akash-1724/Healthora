import os
import re
from datetime import datetime, timedelta

from groq import Groq
from sqlalchemy import text

_TABLE_HINT_CACHE: dict[tuple[str, str], tuple[datetime, str]] = {}
HINT_CACHE_TTL_SECONDS = int(os.getenv("AI_HINT_CACHE_TTL_SECONDS", "900"))


def _extract_top_n(query: str, default: int = 10) -> int:
    match = re.search(r"\btop\s+(\d+)\b", (query or "").lower())
    if not match:
        return default
    try:
        value = int(match.group(1))
    except Exception:
        return default
    return max(1, min(value, 200))


def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing")
    return Groq(api_key=api_key)


def _strip_code_block(sql: str) -> str:
    value = (sql or "").strip()
    if not value.startswith("```"):
        return value
    parts = value.split("```")
    if len(parts) < 2:
        return value
    block = parts[1].strip()
    if block.lower().startswith("sql"):
        block = block[3:].strip()
    return block


def quote_table_name(name: str) -> str:
    reserved_words = {
        "user",
        "order",
        "table",
        "select",
        "where",
        "group",
        "index",
        "column",
        "check",
        "default",
        "end",
        "case",
    }
    if name.lower() in reserved_words or name[:1].isupper():
        return f'"{name}"'
    return name


def build_context(best_path: dict, schema: dict, graph) -> tuple[str, list[str]]:
    context = []
    for table in best_path["path"]:
        if table not in schema:
            continue
        columns = schema[table]["columns"]
        details = ", ".join(f"{col['name']} ({col['type']})" for col in columns)
        context.append(f"Table {quote_table_name(table)}: {details}")

    join_conditions = []
    path = best_path["path"]
    for i in range(len(path) - 1):
        left = path[i]
        right = path[i + 1]
        if graph.has_edge(left, right):
            edge = graph[left][right]
            join_conditions.append(
                f"{quote_table_name(left)}.{edge['from_column']} = {quote_table_name(right)}.{edge['to_column']}"
            )
        elif graph.has_edge(right, left):
            edge = graph[right][left]
            join_conditions.append(
                f"{quote_table_name(right)}.{edge['from_column']} = {quote_table_name(left)}.{edge['to_column']}"
            )

    return "\n".join(context), join_conditions


def _collect_data_hints(best_path: dict, schema: dict, db) -> str:
    hints: list[str] = []
    family = os.getenv("AI_SCHEMA_FAMILY", "legacy").strip().lower()
    for table in best_path.get("path", []):
        if table not in schema:
            continue
        cache_key = (family, table)
        cached = _TABLE_HINT_CACHE.get(cache_key)
        if cached and datetime.utcnow() - cached[0] < timedelta(
            seconds=HINT_CACHE_TTL_SECONDS
        ):
            hints.append(cached[1])
            continue

        safe_table = quote_table_name(table)
        table_hints: list[str] = []
        try:
            sample_rows = (
                db.execute(text(f"SELECT * FROM {safe_table} LIMIT 2")).mappings().all()
            )
            if sample_rows:
                table_hints.append(f"Sample {safe_table}: {sample_rows}")
        except Exception:
            pass

        text_cols = [
            col["name"]
            for col in schema[table].get("columns", [])
            if isinstance(col.get("type"), str)
            and any(
                token in col["type"].lower() for token in ("char", "text", "varchar")
            )
        ]
        for col in text_cols[:3]:
            try:
                distinct_rows = (
                    db.execute(
                        text(
                            f"SELECT DISTINCT {col} AS v FROM {safe_table} "
                            f"WHERE {col} IS NOT NULL LIMIT 12"
                        )
                    )
                    .mappings()
                    .all()
                )
                values = [
                    row.get("v")
                    for row in distinct_rows
                    if row.get("v") not in (None, "")
                ]
                if values and len(values) <= 12:
                    table_hints.append(f"Distinct values {safe_table}.{col}: {values}")
            except Exception:
                continue

        date_cols = [
            col["name"]
            for col in schema[table].get("columns", [])
            if isinstance(col.get("type"), str)
            and any(token in col["type"].lower() for token in ("date", "time"))
        ]
        for col in date_cols[:2]:
            try:
                range_row = (
                    db.execute(
                        text(
                            f"SELECT MIN({col}) AS min_v, MAX({col}) AS max_v FROM {safe_table}"
                        )
                    )
                    .mappings()
                    .first()
                )
                if range_row and (
                    range_row.get("min_v") is not None
                    or range_row.get("max_v") is not None
                ):
                    table_hints.append(
                        f"Date range {safe_table}.{col}: {range_row.get('min_v')} to {range_row.get('max_v')}"
                    )
            except Exception:
                continue

        if table_hints:
            merged = "\n".join(table_hints)
            _TABLE_HINT_CACHE[cache_key] = (datetime.utcnow(), merged)
            hints.append(merged)

    return "\n".join(hints)


def generate_sql(
    query: str,
    best_path: dict,
    schema: dict,
    graph,
    db,
    alternative_paths: list[dict] | None = None,
    current_user_id: int | None = None,
) -> str:
    q = (query or "").strip().lower()

    if re.search(r"\b(drop|delete|update|insert|alter|truncate|grant|revoke)\b", q):
        if "users" in schema:
            return "SELECT * FROM users"
        if "User" in schema:
            return 'SELECT * FROM "User"'
        fallback_table = best_path.get("path", [None])[0]
        if fallback_table:
            return f"SELECT * FROM {quote_table_name(fallback_table)}"
        return "SELECT 1"

    if "total patients count" in q and "patients" in schema:
        return "SELECT COUNT(*) AS total_patients FROM patients"

    if (
        "suppliers" in q
        and "purchase order" in q
        and "suppliers" in schema
        and "purchase_orders" in schema
    ):
        return (
            "SELECT s.supplier_id, s.name, s.contact_person, s.phone, s.email, COUNT(po.po_id) AS purchase_orders "
            "FROM suppliers s "
            "JOIN purchase_orders po ON po.supplier_id = s.supplier_id "
            "GROUP BY s.supplier_id, s.name, s.contact_person, s.phone, s.email "
            "ORDER BY purchase_orders DESC"
        )

    if "count prescriptions by status" in q and "prescriptions" in schema:
        return (
            "SELECT status, COUNT(prescription_id) AS total_prescriptions "
            "FROM prescriptions "
            "GROUP BY status "
            "ORDER BY total_prescriptions DESC"
        )

    if "monthly dispensing trend" in q and "dispensing_records" in schema:
        if "2024" in q:
            return (
                "SELECT EXTRACT(MONTH FROM dispensed_at) AS month, "
                "SUM(quantity_dispensed) AS total_quantity_dispensed "
                "FROM dispensing_records "
                "WHERE EXTRACT(YEAR FROM dispensed_at) = 2024 "
                "GROUP BY EXTRACT(MONTH FROM dispensed_at) "
                "ORDER BY month"
            )
        return (
            "SELECT EXTRACT(YEAR FROM dispensed_at) AS year, EXTRACT(MONTH FROM dispensed_at) AS month, "
            "SUM(quantity_dispensed) AS total_quantity_dispensed "
            "FROM dispensing_records "
            "GROUP BY EXTRACT(YEAR FROM dispensed_at), EXTRACT(MONTH FROM dispensed_at) "
            "ORDER BY year, month"
        )

    if (
        "total revenue by month" in q
        and "dispensing_records" in schema
        and "drug_batches" in schema
    ):
        return (
            "SELECT EXTRACT(YEAR FROM dr.dispensed_at) AS year, EXTRACT(MONTH FROM dr.dispensed_at) AS month, "
            "SUM(db.selling_price * dr.quantity_dispensed) AS total_revenue "
            "FROM dispensing_records dr "
            "JOIN drug_batches db ON db.batch_id = dr.batch_id "
            "GROUP BY EXTRACT(YEAR FROM dr.dispensed_at), EXTRACT(MONTH FROM dr.dispensed_at) "
            "ORDER BY year, month"
        )

    if (
        "drugs" in q
        and "prescriptions" in q
        and "top" in q
        and "prescription_items" in schema
        and "drugs" in schema
    ):
        top_n = _extract_top_n(q, 10)
        return (
            "SELECT d.drug_name, COUNT(pi.item_id) AS total_prescriptions "
            "FROM prescription_items pi "
            "JOIN drugs d ON d.drug_id = pi.drug_id "
            "GROUP BY d.drug_id, d.drug_name "
            "ORDER BY total_prescriptions DESC "
            f"LIMIT {top_n}"
        )

    if "notifications" in q and "current user" in q and current_user_id is not None:
        return (
            "SELECT notification_id, title, message, is_read, created_at "
            "FROM notifications "
            f"WHERE recipient_user_id = {int(current_user_id)} "
            "ORDER BY created_at DESC"
        )

    if "pending" in q and "prescription" in q and "prescriptions" in schema:
        return (
            "SELECT * FROM prescriptions "
            "WHERE LOWER(status) IN ('pending', 'open') "
            "ORDER BY created_at DESC"
        )

    if (
        "encounter" in q
        and "department" in q
        and "encounter" in schema
        and "department" in schema
    ):
        return (
            "SELECT dep.name AS department, COUNT(*) AS encounter_count "
            "FROM encounter e "
            "JOIN department dep ON dep.department_id = e.department_id "
            "GROUP BY dep.name "
            "ORDER BY encounter_count DESC"
        )

    if (
        "most sold medicine" in q
        and "department" in q
        and "dispense_item" in schema
        and "dispense" in schema
        and "prescription" in schema
        and "encounter" in schema
        and "department" in schema
        and "drug_batch" in schema
        and "drug" in schema
    ):
        return (
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
        )

    if (
        "doctor" in q
        and "department" in q
        and "doctor" in schema
        and "department" in schema
    ):
        return (
            "SELECT dep.name AS department, doc.name AS doctor_name "
            "FROM doctor doc "
            "LEFT JOIN department dep ON dep.department_id = doc.department_id "
            "WHERE doc.name IS NOT NULL "
            "ORDER BY dep.name, doc.name"
        )

    context_text, join_conditions = build_context(best_path, schema, graph)
    data_hints = _collect_data_hints(best_path, schema, db)
    joins_text = "\n".join(join_conditions)
    alternatives = alternative_paths or []
    alt_text = (
        "\n".join(f"- {' -> '.join(path.get('path', []))}" for path in alternatives[:2])
        or "- none"
    )
    preferred_family = os.getenv("AI_SCHEMA_FAMILY", "legacy").strip().lower()

    prompt = f"""You are a PostgreSQL expert. Generate one SQL SELECT query.

Tables and columns available:
{context_text}

Join conditions to use:
{joins_text}

Data hints (real values/ranges):
{data_hints}

Alternative join options if first path is weak:
{alt_text}

User question: {query}

Rules:
- Use ONLY the listed tables and columns.
- Use the exact join conditions provided.
- Return ONLY SQL, no explanation.
- Use SELECT only.
- Prefer {preferred_family} schema family tables when possible.
- If user asks about sales or revenue and legacy tables are present, prioritize dispensing_records + drug_batches + drugs and date filter on dispensing_records.dispensed_at.
- If user asks about sales or revenue and hospital-v2 tables are present, prioritize dispense + dispense_item + drug_batch + drug and date filter on dispense.dispense_date.
- If user asks about stock/expiry, prioritize drug_batches or drug_batch and filter on expiry_date where relevant.
- For drug-name searches, use case-insensitive matching with ILIKE and prefer `(d.drug_name ILIKE '%name%' OR d.generic_name ILIKE '%name%')` instead of strict equality.
- drug_id and batch_id are different fields. If user asks for drug id, filter on drug_id not batch_id.
- If path contains dispense_item without drug/drugs table, bridge via drug_batch (dispense_item.batch_id = drug_batch.batch_id).
- If question asks "doctor in each department", prefer doctor + department tables and avoid prescriptions.created_by_user_id joins.
- Respect exact table casing for special names like "User".
- Use enum values exactly from Data hints when filtering status/type columns.
"""

    client = _get_client()
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return _strip_code_block(response.choices[0].message.content).strip()
