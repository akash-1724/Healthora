import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

_MODEL = None
SIMILARITY_THRESHOLD = float(os.getenv("AI_RAG_THRESHOLD", "0.92"))
MAX_STORE_SIZE = int(os.getenv("AI_RAG_MAX_STORE_SIZE", "500"))
RAG_STORE_PATH = Path(__file__).resolve().parent.parent / "ai_rag_store.json"
DEBUG = os.getenv("AI_DEBUG_NL2SQL", "false").strip().lower() == "true"


def _model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def normalize_query_for_similarity(query: str) -> str:
    normalized = query.lower()
    normalized = re.sub(r"\b\d+\b", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def compute_schema_hash(schema: dict) -> str:
    serialized = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def load_store() -> list[dict]:
    if not RAG_STORE_PATH.exists():
        return []
    try:
        return json.loads(RAG_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_store(store: list[dict]) -> None:
    if len(store) > MAX_STORE_SIZE:
        store = store[-MAX_STORE_SIZE:]
    RAG_STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def find_similar_query(query: str, store: list[dict], schema: dict, threshold: float = SIMILARITY_THRESHOLD) -> tuple[dict | None, float]:
    if not store:
        if DEBUG:
            print("[RAG] empty store")
        return None, 0.0

    current_schema_hash = compute_schema_hash(schema)
    compatible_store = [entry for entry in store if entry.get("schema_hash") == current_schema_hash]
    stale_count = len(store) - len(compatible_store)
    if DEBUG and stale_count > 0:
        print(f"[RAG] ignoring stale entries due to schema mismatch: {stale_count}")
    if not compatible_store:
        if DEBUG:
            print("[RAG] no schema-compatible entries")
        return None, 0.0

    normalized_query = normalize_query_for_similarity(query)
    model = _model()
    query_embedding = model.encode([normalized_query])
    stored_queries = [entry.get("normalized_query") or normalize_query_for_similarity(entry["query"]) for entry in compatible_store]
    stored_embeddings = model.encode(stored_queries)

    similarities = cosine_similarity(query_embedding, stored_embeddings)[0]
    best_idx = int(np.argmax(similarities))
    best_score = float(similarities[best_idx])

    if best_score >= threshold:
        if DEBUG:
            print(f"[RAG] hit score={best_score:.4f} query='{compatible_store[best_idx].get('query', '')}'")
        return compatible_store[best_idx], best_score
    if DEBUG:
        print(f"[RAG] miss best_score={best_score:.4f} threshold={threshold:.4f}")
    return None, best_score


def save_successful_query(query: str, best_path: dict, sql: str, result_count: int, schema: dict) -> None:
    store = load_store()
    normalized_query = normalize_query_for_similarity(query)
    schema_hash = compute_schema_hash(schema)

    for entry in store:
        if entry.get("query", "").lower() == query.lower() and entry.get("schema_hash") == schema_hash:
            entry["sql"] = sql
            entry["best_path"] = best_path
            entry["result_count"] = result_count
            entry["normalized_query"] = normalized_query
            entry["last_used"] = datetime.utcnow().isoformat()
            entry["use_count"] = entry.get("use_count", 1) + 1
            save_store(store)
            if DEBUG:
                print(f"[RAG] updated existing entry query='{query}'")
            return

    store.append(
        {
            "query": query,
            "best_path": best_path,
            "sql": sql,
            "result_count": result_count,
            "normalized_query": normalized_query,
            "schema_hash": schema_hash,
            "saved_at": datetime.utcnow().isoformat(),
            "last_used": datetime.utcnow().isoformat(),
            "use_count": 1,
        }
    )
    save_store(store)
    if DEBUG:
        print(f"[RAG] saved new entry query='{query}'")


def get_rag_stats() -> dict:
    store = load_store()
    return {
        "total": len(store),
        "entries": [
            {
                "query": entry.get("query"),
                "path": entry.get("best_path", {}).get("path", []),
                "use_count": entry.get("use_count", 1),
                "result_count": entry.get("result_count", 0),
                "saved_at": entry.get("saved_at"),
            }
            for entry in store
        ],
    }


def clear_store() -> None:
    if RAG_STORE_PATH.exists():
        RAG_STORE_PATH.unlink()
