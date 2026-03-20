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


def score_keyword_boost(query: str, path: list[str]) -> float:
    query_words = set(query.lower().split())
    keyword_map = {
        "prescription": {"prescriptions", "prescription_items"},
        "prescribed": {"prescriptions", "prescription_items"},
        "dispense": {"dispensing_records"},
        "dispensed": {"dispensing_records"},
        "sale": {"dispensing_records", "drugs", "drug_batches"},
        "revenue": {"dispensing_records", "drugs", "drug_batches"},
        "stock": {"drug_batches"},
        "expiry": {"drug_batches"},
        "supplier": {"suppliers", "purchase_orders", "purchase_order_items"},
        "order": {"purchase_orders", "purchase_order_items"},
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

    return min(boost, 0.3)


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

        final_score = (semantic_score * 0.78) + (length_score * 0.12) + (nullable_score * 0.10) + keyword_boost
        results.append(
            {
                "path": path,
                "description": description,
                "semantic_score": round(semantic_score, 4),
                "length_score": round(length_score, 4),
                "nullable_score": round(nullable_score, 4),
                "final_score": round(final_score, 4),
            }
        )

    results.sort(key=lambda item: item["final_score"], reverse=True)
    return results
