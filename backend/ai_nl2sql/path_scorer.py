import os

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

_MODEL = None
DEBUG = os.getenv("AI_DEBUG_NL2SQL", "false").strip().lower() == "true"
SEMANTIC_WEIGHT = float(os.getenv("AI_PATH_SEMANTIC_WEIGHT", "0.76"))
LENGTH_WEIGHT = float(os.getenv("AI_PATH_LENGTH_WEIGHT", "0.10"))
NULLABLE_WEIGHT = float(os.getenv("AI_PATH_NULLABLE_WEIGHT", "0.10"))


def _model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


TABLE_DESCRIPTIONS = {
    "hospital": "hospital institution facility",
    "department": "hospital department unit ward",
    "role": "role permissions access",
    "User": "system user staff pharmacist doctor",
    "patient": "patient medical records",
    "doctor": "doctor physician specialist",
    "encounter": "hospital visit admission encounter",
    "manufacturer": "drug manufacturer",
    "drug": "medicine drug catalog",
    "drug_batch": "drug batch stock expiry",
    "pharmacy_store": "pharmacy counter store",
    "store_inventory": "store inventory stock",
    "supplier": "supplier vendor procurement",
    "purchase_order": "purchase order",
    "purchase_order_item": "purchase order items",
    "stock_transaction": "stock movement transaction",
    "prescription": "doctor prescription",
    "prescription_detail": "prescribed drug details",
    "dispense": "dispensing event",
    "dispense_item": "dispensed batch quantity",
    "pharmacy_bill": "pharmacy bill",
    "pharmacy_bill_item": "bill line items",
    "controlled_drug_log": "controlled substance log",
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


def score_keyword_boost(query: str, path: list[str]) -> float:
    query_words = set(query.lower().split())
    keyword_map = {
        "prescription": {
            "prescription",
            "prescription_detail",
            "prescriptions",
            "prescription_items",
        },
        "prescribed": {
            "prescription",
            "prescription_detail",
            "prescriptions",
            "prescription_items",
        },
        "dispense": {"dispense", "dispense_item", "dispensing_records"},
        "dispensed": {"dispense", "dispense_item", "dispensing_records"},
        "sale": {"dispense", "dispense_item", "dispensing_records", "drug", "drugs"},
        "revenue": {"pharmacy_bill", "pharmacy_bill_item", "dispensing_records"},
        "stock": {"store_inventory", "stock_transaction", "drug_batch", "drug_batches"},
        "expiry": {"drug_batch", "drug_batches"},
        "supplier": {"supplier", "suppliers", "purchase_order", "purchase_orders"},
        "order": {
            "purchase_order",
            "purchase_order_item",
            "purchase_orders",
            "purchase_order_items",
        },
        "doctor": {"doctor", "prescription", "prescriptions", "encounter"},
        "department": {"department", "encounter"},
        "audit": {"audit_logs"},
        "notification": {"notifications"},
    }

    boost = 0.0
    for word in query_words:
        tables = keyword_map.get(word)
        if not tables:
            continue
        if any(table in path for table in tables):
            boost += 0.12

    return min(boost, 0.35)


def score_domain_modifier(query: str, path: list[str]) -> float:
    q = query.lower()
    path_set = set(path)
    must_cover = {
        "patient": {"patient", "patients"},
        "doctor": {"doctor", "prescription", "prescriptions"},
        "supplier": {"supplier", "suppliers", "purchase_order", "purchase_orders"},
        "inventory": {"drug_batch", "drug_batches", "store_inventory"},
        "dispense": {"dispense", "dispense_item", "dispensing_records"},
    }

    modifier = 0.0
    for keyword, expected_tables in must_cover.items():
        if keyword in q:
            modifier += 0.08 if (expected_tables & path_set) else -0.08
    return max(-0.3, min(0.3, modifier))


def path_to_description(path: list[str]) -> str:
    parts = [TABLE_DESCRIPTIONS.get(table, table) for table in path]
    return " -> ".join(parts)


def score_path_length(path: list[str]) -> float:
    max_length = 5
    return max(0.0, (max_length - len(path)) / max_length)


def score_semantic_similarity(query: str, path_description: str) -> float:
    model = _model()
    query_embedding = model.encode([query])
    path_embedding = model.encode([path_description])
    return float(cosine_similarity(query_embedding, path_embedding)[0][0])


def score_nullable_columns(path: list[str], schema: dict) -> float:
    score = 1.0
    for table in path:
        for col in schema.get(table, {}).get("columns", []):
            if col.get("nullable") == "YES":
                score -= 0.05
    return max(0.0, score)


def score_all_paths(query: str, paths: list[list[str]], schema: dict) -> list[dict]:
    results = []
    for path in paths:
        description = path_to_description(path)
        semantic_score = score_semantic_similarity(query, description)
        length_score = score_path_length(path)
        nullable_score = score_nullable_columns(path, schema)
        keyword_boost = score_keyword_boost(query, path)
        domain_modifier = score_domain_modifier(query, path)

        final_score = (
            (semantic_score * SEMANTIC_WEIGHT)
            + (length_score * LENGTH_WEIGHT)
            + (nullable_score * NULLABLE_WEIGHT)
            + keyword_boost
            + domain_modifier
        )
        result = {
            "path": path,
            "description": description,
            "semantic_score": round(semantic_score, 4),
            "length_score": round(length_score, 4),
            "nullable_score": round(nullable_score, 4),
            "keyword_boost": round(keyword_boost, 4),
            "domain_modifier": round(domain_modifier, 4),
            "final_score": round(final_score, 4),
        }
        results.append(result)

    results.sort(key=lambda item: item["final_score"], reverse=True)
    if DEBUG and results:
        print(
            f"[SCORER] top_path={results[0]['path']} score={results[0]['final_score']}"
        )
    return results
