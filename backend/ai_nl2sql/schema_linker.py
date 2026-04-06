import os
import re

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

_MODEL = None
_DESC_EMBEDDINGS = {}
DEBUG = os.getenv("AI_DEBUG_NL2SQL", "false").strip().lower() == "true"
SCHEMA_FAMILY = os.getenv("AI_SCHEMA_FAMILY", "legacy").strip().lower()


def _model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        try:
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _MODEL = False
    return _MODEL


def _token_overlap_score(query: str, text: str) -> float:
    q = set(re.findall(r"[a-z0-9_]+", (query or "").lower()))
    t = set(re.findall(r"[a-z0-9_]+", (text or "").lower()))
    if not q or not t:
        return 0.0
    return len(q.intersection(t)) / max(1, len(q))


TABLE_DESCRIPTIONS = {
    # hospital-v2 schema
    "hospital": "hospital institution facility registration",
    "department": "hospital department unit ward",
    "role": "user role permission access",
    "User": "system user staff pharmacist doctor login",
    "patient": "patient personal medical records demographics",
    "doctor": "doctor physician specialist",
    "encounter": "hospital visit admission consultation encounter",
    "manufacturer": "drug manufacturer company producer",
    "drug": "medicine drug catalog",
    "drug_batch": "drug inventory batch stock expiry prices",
    "pharmacy_store": "pharmacy store counter location",
    "store_inventory": "store stock inventory quantity",
    "supplier": "supplier vendor procurement",
    "purchase_order": "purchase order to supplier",
    "purchase_order_item": "ordered drug items quantities",
    "stock_transaction": "stock movement in out transaction",
    "prescription": "doctor prescription",
    "prescription_detail": "prescribed drug dosage frequency duration",
    "dispense": "dispensed prescription by pharmacist",
    "dispense_item": "dispensed item batch quantity",
    "pharmacy_bill": "pharmacy billing payment invoice",
    "pharmacy_bill_item": "billed drug quantity price",
    "controlled_drug_log": "controlled substance narcotic log",
    # legacy app schema
    "roles": "role permissions access control",
    "users": "staff users pharmacists admins",
    "patients": "patient demographic and medical profile",
    "drugs": "drug medicine catalog",
    "drug_batches": "drug inventory batches stock expiry prices",
    "suppliers": "supplier vendor details",
    "purchase_orders": "purchase orders to suppliers",
    "purchase_order_items": "items and quantities in purchase orders",
    "prescriptions": "prescriptions written by doctors",
    "prescription_items": "drug and quantity prescribed",
    "dispensing_records": "dispensed drugs quantities and dates",
    "audit_logs": "audit history and actions",
    "notifications": "notifications and alerts",
}


V2_PRIORITY_TABLES = {
    "hospital",
    "department",
    "role",
    "User",
    "patient",
    "doctor",
    "encounter",
    "manufacturer",
    "drug",
    "drug_batch",
    "pharmacy_store",
    "store_inventory",
    "supplier",
    "purchase_order",
    "purchase_order_item",
    "stock_transaction",
    "prescription",
    "prescription_detail",
    "dispense",
    "dispense_item",
    "pharmacy_bill",
    "pharmacy_bill_item",
    "controlled_drug_log",
}


def detect_entity_tables(query: str) -> list[str]:
    q = query.lower()
    entity_map = {
        "patient": ["patient", "patients"],
        "doctor": ["doctor", "prescription", "prescriptions"],
        "pharmacist": ["User", "users", "dispense", "dispensing_records"],
        "user": ["User", "users", "role", "roles"],
        "department": ["department", "encounter"],
        "hospital": ["hospital", "department"],
        "encounter": ["encounter", "patient", "doctor"],
        "admission": ["encounter", "patient", "department"],
        "medicine": ["drug", "drug_batch", "drugs", "drug_batches"],
        "drug": ["drug", "drug_batch", "drugs", "drug_batches"],
        "batch": ["drug_batch", "drug_batches", "dispense_item", "dispensing_records"],
        "stock": ["store_inventory", "stock_transaction", "drug_batch", "drug_batches"],
        "inventory": ["store_inventory", "drug_batch", "drug_batches"],
        "supplier": ["supplier", "suppliers", "purchase_order", "purchase_orders"],
        "order": [
            "purchase_order",
            "purchase_order_item",
            "purchase_orders",
            "purchase_order_items",
        ],
        "purchase": [
            "purchase_order",
            "purchase_order_item",
            "purchase_orders",
            "purchase_order_items",
        ],
        "prescription": [
            "prescription",
            "prescription_detail",
            "prescriptions",
            "prescription_items",
        ],
        "dispense": ["dispense", "dispense_item", "dispensing_records"],
        "sales": [
            "dispense",
            "dispense_item",
            "dispensing_records",
            "pharmacy_bill",
            "pharmacy_bill_item",
        ],
        "transaction": ["stock_transaction", "dispensing_records", "pharmacy_bill"],
        "transactions": ["stock_transaction", "dispensing_records", "pharmacy_bill"],
        "revenue": ["pharmacy_bill", "pharmacy_bill_item", "dispensing_records"],
        "medication": ["drug", "drug_batch", "drugs", "drug_batches"],
        "visit": ["encounter", "prescription", "prescriptions", "patient", "patients"],
        "billing": ["pharmacy_bill", "pharmacy_bill_item"],
        "bill": ["pharmacy_bill", "pharmacy_bill_item"],
        "controlled": ["controlled_drug_log"],
        "narcotic": ["controlled_drug_log"],
        "audit": ["audit_logs"],
        "notification": ["notifications"],
    }

    forced = []
    for keyword, tables in entity_map.items():
        if keyword in q:
            forced.extend(tables)
    return sorted(set(forced))


def _v2_boost(table: str, has_v2_tables: bool) -> float:
    if not has_v2_tables:
        return 0.0
    if SCHEMA_FAMILY == "legacy":
        return 0.0
    return 0.06 if table in V2_PRIORITY_TABLES else 0.0


def _is_v2_table(table: str) -> bool:
    return table in V2_PRIORITY_TABLES


def _is_legacy_table(table: str) -> bool:
    return table in {
        "roles",
        "users",
        "patients",
        "drugs",
        "drug_batches",
        "suppliers",
        "purchase_orders",
        "purchase_order_items",
        "prescriptions",
        "prescription_items",
        "dispensing_records",
        "audit_logs",
        "notifications",
    }


def _family_filter(schema: dict) -> list[str]:
    tables = list(schema.keys())
    if SCHEMA_FAMILY == "legacy":
        filtered = [table for table in tables if _is_legacy_table(table)]
        return filtered or tables
    if SCHEMA_FAMILY == "v2":
        filtered = [table for table in tables if _is_v2_table(table)]
        return filtered or tables
    return tables


def get_relevant_tables(query: str, schema: dict, top_k: int = 10) -> list[str]:
    allowed_tables = _family_filter(schema)
    allowed_set = set(allowed_tables)
    available = set(schema.keys())
    forced_tables = [
        table for table in detect_entity_tables(query) if table in available
    ]
    forced_tables = [table for table in forced_tables if table in allowed_set]
    has_v2_tables = any(table in available for table in V2_PRIORITY_TABLES)

    model = _model()
    query_embedding = model.encode([query]) if model else None
    scored = []
    for table in allowed_tables:
        description = TABLE_DESCRIPTIONS.get(table, table)
        columns = schema.get(table, {}).get("columns", [])
        if columns:
            column_names = ", ".join(
                col.get("name", "") for col in columns if col.get("name")
            )
            if column_names:
                description = f"{description} columns: {column_names}"
        if model:
            if description not in _DESC_EMBEDDINGS:
                _DESC_EMBEDDINGS[description] = model.encode([description])
            table_embedding = _DESC_EMBEDDINGS[description]
            similarity = float(
                cosine_similarity(query_embedding, table_embedding)[0][0]
            )
        else:
            similarity = _token_overlap_score(query, description)
        similarity += _v2_boost(table, has_v2_tables)
        scored.append((table, similarity))

    scored.sort(key=lambda item: item[1], reverse=True)

    score_map = {table: score for table, score in scored}
    if len(forced_tables) > top_k:
        forced_tables = sorted(
            forced_tables, key=lambda t: score_map.get(t, -1.0), reverse=True
        )[:top_k]

    final_tables = list(forced_tables)
    for table, _ in scored:
        if len(final_tables) >= top_k:
            break
        if table not in final_tables:
            final_tables.append(table)

    if DEBUG:
        print(f"[LINKER] forced={forced_tables}")
        print(f"[LINKER] final={final_tables}")
        print(f"[LINKER] family={SCHEMA_FAMILY} allowed_count={len(allowed_tables)}")
        print(f"[LINKER] top_scored={scored[:8]}")

    return final_tables
