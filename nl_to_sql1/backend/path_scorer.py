from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')

TABLE_DESCRIPTIONS = {
    "patients": "patient personal medical records",
    "users": "system user staff pharmacist",
    "drugs": "medicine medication pharmaceutical",
    "drug_batches": "drug inventory batch stock",
    "prescriptions": "prescribed medication drugs ordered by doctor",
    "prescription_items": "prescribed drug details dosage frequency",
    "dispensing_records": "dispensed drug item quantity",
    "purchase_orders": "supplier purchase order procurement",
    "purchase_order_items": "ordered drug item from supplier",
    "suppliers": "drug supplier vendor",
    "roles": "user role permission access",
    "audit_logs": "audit trail activity logs",
    "notifications": "alerts notification messages",
    "patient": "patient personal medical records",
    "doctor": "doctor physician medical staff",
    "encounter": "hospital visit admission consultation",
    "prescription": "prescribed medication drugs ordered by doctor",
    "prescription_detail": "prescribed drug details dosage frequency",
    "drug": "medicine medication pharmaceutical",
    "drug_batch": "drug inventory batch stock",
    "controlled_drug_log": "controlled substance narcotic log record",
    "dispense": "dispensed given medication pharmacy",
    "dispense_item": "dispensed drug item quantity",
    "pharmacy_bill": "pharmacy billing payment invoice",
    "pharmacy_bill_item": "billed drug item price",
    "store_inventory": "pharmacy store stock inventory",
    "pharmacy_store": "pharmacy store location",
    "purchase_order": "supplier purchase order procurement",
    "purchase_order_item": "ordered drug item from supplier",
    "stock_transaction": "stock movement in out transaction",
    "manufacturer": "drug manufacturer company producer",
    "supplier": "drug supplier vendor",
    "hospital": "hospital institution facility",
    "department": "hospital department unit ward",
    "role": "user role permission access",
    "User": "system user staff pharmacist",
}

def score_keyword_boost(query, path):
    query_words = set(query.lower().split())
    boost = 0.0

    keyword_map = {
        "prescribed": ["prescription", "prescription_detail", "prescriptions", "prescription_items"],
        "prescription": ["prescription", "prescription_detail", "prescriptions", "prescription_items"],
        "dispensed": ["dispense", "dispense_item", "dispensing_records"],
        "stock": ["store_inventory", "stock_transaction", "drug_batches"],
        "ordered": ["purchase_order", "purchase_order_item", "purchase_orders", "purchase_order_items"],
        "batch": ["drug_batch", "drug_batches"],
        "billed": ["pharmacy_bill", "pharmacy_bill_item"],
        "controlled": ["controlled_drug_log"],
        "encounter": ["encounter"],
        "admitted": ["encounter"],
    }

    for word in query_words:
        if word in keyword_map:
            for table in keyword_map[word]:
                if table in path:
                    boost += 0.15

    return min(boost, 0.3)

def path_to_description(path, G):
    parts = []
    for table in path:
        parts.append(TABLE_DESCRIPTIONS.get(table) or str(table))
    return " -> ".join(parts)

def score_path_length(path):
    max_length = 5
    return max(0, (max_length - len(path)) / max_length)

def score_semantic_similarity(query, path_description):
    query_embedding = model.encode([query])
    path_embedding = model.encode([path_description])
    similarity = cosine_similarity(query_embedding, path_embedding)[0][0]
    return float(similarity)

def score_nullable_fks(path, schema):
    score = 1.0
    for table in path:
        if table in schema:
            for col in schema[table]["columns"]:
                if col["nullable"] == "YES":
                    score -= 0.1
    return max(0, score)

def score_all_paths(query, paths, G, schema):
    results = []

    for path in paths:
        description = path_to_description(path, G)
        length_score = score_path_length(path)
        semantic_score = score_semantic_similarity(query, description)
        nullable_score = score_nullable_fks(path, schema)
        keyword_boost = score_keyword_boost(query, path)

        final_score = (
            semantic_score * 0.8 +
            length_score * 0.1 +
            nullable_score * 0.1 +
            keyword_boost
        )

        results.append({
            "path": path,
            "description": description,
            "final_score": round(final_score, 4),
            "semantic_score": round(semantic_score, 4),
            "length_score": round(length_score, 4),
            "nullable_score": round(nullable_score, 4)
        })

    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results


if __name__ == "__main__":
    from db_introspection import introspect_database
    from graph_builder import build_graph, get_join_paths
    import os
    from dotenv import load_dotenv

    load_dotenv()

    schema = introspect_database(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    G = build_graph(schema)
    query = "show me  drugs prescribed to a patient"
    paths = get_join_paths(G, "patient", "drug")

    print(f"Query: {query}")
    print(f"Scoring {len(paths)} paths...\n")

    scored = score_all_paths(query, paths, G, schema)

    for i, result in enumerate(scored[:3]):
        print(f"Rank {i+1}: {' → '.join(result['path'])}")
        print(f"  Final Score:    {result['final_score']}")
        print(f"  Semantic Score: {result['semantic_score']}")
        print()
