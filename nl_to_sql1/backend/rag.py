import json
import os
import re
import hashlib
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

RAG_STORE_PATH = os.path.join(os.path.dirname(__file__), "rag_store.json")
SIMILARITY_THRESHOLD = 0.92
MAX_STORE_SIZE = 500

model = SentenceTransformer('all-MiniLM-L6-v2')

def normalize_query_for_similarity(query):
    normalized = query.lower()
    normalized = re.sub(r"\b\d+\b", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized

def compute_schema_hash(schema):
    serialized = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def load_store():
    if not os.path.exists(RAG_STORE_PATH):
        return []
    with open(RAG_STORE_PATH, "r") as f:
        return json.load(f)

def save_store(store):
    if len(store) > MAX_STORE_SIZE:
        store = store[-MAX_STORE_SIZE:]
    with open(RAG_STORE_PATH, "w") as f:
        json.dump(store, f, indent=2)

def find_similar_query(query, store, schema, threshold=SIMILARITY_THRESHOLD):
    if not store:
        return None, 0.0

    current_schema_hash = compute_schema_hash(schema)
    compatible_store = [
        entry for entry in store
        if entry.get("schema_hash") == current_schema_hash
    ]

    stale_count = len(store) - len(compatible_store)
    if stale_count:
        print(f"[RAG] ⚠️ Ignoring {stale_count} stale cache entries (schema mismatch)")

    if not compatible_store:
        print("[RAG] No schema-compatible cache entries found.")
        return None, 0.0

    normalized_query = normalize_query_for_similarity(query)
    query_embedding = model.encode([normalized_query])
    stored_queries = [
        entry.get("normalized_query") or normalize_query_for_similarity(entry["query"])
        for entry in compatible_store
    ]
    stored_embeddings = model.encode(stored_queries)

    similarities = cosine_similarity(query_embedding, stored_embeddings)[0]
    best_idx = int(np.argmax(similarities))
    best_score = float(similarities[best_idx])

    if best_score >= threshold:
        entry = compatible_store[best_idx]
        print(f"[RAG] ✅ Similar query found (similarity: {best_score:.3f})")
        print(f"[RAG] Matched: '{entry['query']}'")
        return entry, best_score

    print(f"[RAG] No match found (best similarity: {best_score:.3f})")
    return None, best_score

def save_successful_query(query, best_path, sql, result_count, schema):
    store = load_store()
    normalized_query = normalize_query_for_similarity(query)
    schema_hash = compute_schema_hash(schema)

    for entry in store:
        if entry["query"].lower() == query.lower() and entry.get("schema_hash") == schema_hash:
            entry["sql"] = sql
            entry["best_path"] = best_path
            entry["result_count"] = result_count
            entry["normalized_query"] = normalized_query
            entry["last_used"] = datetime.now().isoformat()
            entry["use_count"] = entry.get("use_count", 1) + 1
            save_store(store)
            print(f"[RAG] 🔄 Updated existing entry for: '{query}'")
            return

    entry = {
        "query": query,
        "best_path": best_path,
        "sql": sql,
        "result_count": result_count,
        "normalized_query": normalized_query,
        "schema_hash": schema_hash,
        "saved_at": datetime.now().isoformat(),
        "last_used": datetime.now().isoformat(),
        "use_count": 1
    }
    store.append(entry)
    save_store(store)
    print(f"[RAG] 💾 Saved new entry: '{query}' → {len(best_path['path'])} table path")

def get_rag_stats():
    store = load_store()
    if not store:
        print("[RAG] Store is empty.")
        return
    print(f"\n[RAG] ── Store Stats ──────────────────")
    print(f"  Total entries:  {len(store)}")
    for entry in store[-5:]:
        path_str = " → ".join(entry["best_path"]["path"])
        print(f"    • '{entry['query']}'")
        print(f"      Path: {path_str}")
        print(f"      Used: {entry.get('use_count', 1)}x | Results: {entry['result_count']}")
    print(f"[RAG] ─────────────────────────────────\n")

def clear_store():
    if os.path.exists(RAG_STORE_PATH):
        os.remove(RAG_STORE_PATH)
        print("[RAG] Store cleared.")
