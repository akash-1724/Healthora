from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

_MODEL = None


def _model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL

TABLE_DESCRIPTIONS = {
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


def detect_entity_tables(query: str) -> list[str]:
    q = query.lower()
    entity_map = {
        "patient": ["patients"],
        "drug": ["drugs", "drug_batches"],
        "medicine": ["drugs", "drug_batches"],
        "stock": ["drug_batches"],
        "inventory": ["drug_batches"],
        "supplier": ["suppliers", "purchase_orders", "purchase_order_items"],
        "purchase": ["purchase_orders", "purchase_order_items"],
        "order": ["purchase_orders", "purchase_order_items"],
        "prescription": ["prescriptions", "prescription_items"],
        "dispense": ["dispensing_records"],
        "sale": ["dispensing_records", "drug_batches", "drugs"],
        "revenue": ["dispensing_records", "drug_batches", "drugs"],
        "audit": ["audit_logs"],
        "notification": ["notifications"],
        "user": ["users", "roles"],
    }

    forced = []
    for keyword, tables in entity_map.items():
        if keyword in q:
            forced.extend(tables)
    return sorted(set(forced))


def get_relevant_tables(query: str, schema: dict, top_k: int = 5) -> list[str]:
    forced_tables = [table for table in detect_entity_tables(query) if table in schema]

    model = _model()
    query_embedding = model.encode([query])
    scored = []
    for table in schema.keys():
        description = TABLE_DESCRIPTIONS.get(table, table)
        table_embedding = model.encode([description])
        similarity = float(cosine_similarity(query_embedding, table_embedding)[0][0])
        scored.append((table, similarity))

    scored.sort(key=lambda item: item[1], reverse=True)

    final_tables = list(forced_tables)
    for table, _ in scored:
        if len(final_tables) >= top_k:
            break
        if table not in final_tables:
            final_tables.append(table)

    return final_tables
