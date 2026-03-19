from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
import os

load_dotenv()

model = SentenceTransformer('all-MiniLM-L6-v2')

TABLE_DESCRIPTIONS = {
    "patients": "patient personal medical records",
    "users": "system user staff pharmacist who dispenses medicine",
    "drugs": "medicine medication pharmaceutical",
    "drug_batches": "drug inventory batch stock expiry",
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
    "User": "system user staff pharmacist who dispenses medicine",
}

def detect_entity_tables(query):
    """Force include tables when query explicitly mentions them"""
    query_lower = query.lower()
    forced = []

    entity_map = {
        "patient": ["patient", "patients"],
        "doctor": ["doctor"],
        "drug": ["drug", "drugs"],
        "medicine": ["drug", "drugs"],
        "user": ["User", "users"],
        "pharmacist": ["User", "users"],
        "supplier": ["supplier", "suppliers"],
        "prescription": ["prescription", "prescriptions"],
        "order": ["purchase_order", "purchase_orders"],
        "dispense": ["dispense", "dispensing_records"],
        "bill": ["pharmacy_bill"],
        "batch": ["drug_batch", "drug_batches"],
        "stock": ["store_inventory", "drug_batches"],
        "inventory": ["store_inventory", "drug_batches"],
        "manufacturer": ["manufacturer"],
        "encounter": ["encounter"],
        "hospital": ["hospital"],
        "department": ["department"],
    }

    for keyword, tables in entity_map.items():
        if keyword in query_lower:
            forced.extend(tables)

    return list(set(forced))


def get_relevant_tables(query, schema, top_k=4):
    forced_tables = [table for table in detect_entity_tables(query) if table in schema]

    query_embedding = model.encode([query])
    scores = []

    for table in schema.keys():
        description = TABLE_DESCRIPTIONS.get(table, table)
        table_embedding = model.encode([description])
        similarity = cosine_similarity(query_embedding, table_embedding)[0][0]

        scores.append({
            "table": table,
            "score": round(float(similarity), 4),
        })

    scores.sort(key=lambda x: x["score"], reverse=True)

    final_tables = list(forced_tables)
    for s in scores:
        if len(final_tables) >= top_k:
            break
        if s["table"] not in final_tables:
            final_tables.append(s["table"])

    print(f"Forced tables: {forced_tables}")
    print(f"Final tables: {final_tables}")

    return final_tables


if __name__ == "__main__":
    from db_introspection import introspect_database

    schema = introspect_database(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    queries = [
        "show me drugs prescribed to a patient",
        "which user dispensed the medicine with drug id 5",
        "show me all purchase orders from a supplier",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        tables = get_relevant_tables(query, schema, top_k=5)
        print(f"Selected: {tables}\n")
