import os
from itertools import combinations

from .graph_builder import get_join_paths
from .path_scorer import score_all_paths
from .rag import find_similar_query, load_store
from .schema_linker import get_relevant_tables

DEBUG = os.getenv("AI_DEBUG_NL2SQL", "false").strip().lower() == "true"


def score_relevant_table_coverage(path: list[str], relevant_tables: list[str]) -> float:
    relevant_set = set(relevant_tables)
    path_set = set(path)

    overlap = len(relevant_set.intersection(path_set))
    irrelevant = len(path_set - relevant_set)

    coverage = overlap / max(1, len(relevant_set))
    penalty = irrelevant * 0.2
    return max(0.0, coverage - penalty)


def run_pipeline(query: str, schema: dict, graph) -> dict | None:
    if DEBUG:
        print("=" * 70)
        print(f"[PIPELINE] query={query}")

    store = load_store()
    rag_match, rag_score = find_similar_query(query, store, schema)
    if rag_match:
        if DEBUG:
            print(f"[PIPELINE] rag_hit score={rag_score:.4f} path={rag_match.get('best_path', {}).get('path', [])}")
        return rag_match.get("best_path")

    relevant_tables = get_relevant_tables(query, schema, top_k=6)
    if DEBUG:
        print(f"[PIPELINE] relevant_tables={relevant_tables}")

    all_paths = []
    for start, end in combinations(relevant_tables, 2):
        all_paths.extend(get_join_paths(graph, start, end))

    unique_paths = []
    seen = set()
    for path in all_paths:
        key = tuple(path)
        if key in seen:
            continue
        seen.add(key)
        unique_paths.append(path)

    if not unique_paths:
        if DEBUG:
            print("[PIPELINE] no join path found")
        return None

    scored = score_all_paths(query, unique_paths, schema)

    for result in scored:
        coverage = score_relevant_table_coverage(result["path"], relevant_tables)
        result["coverage_bonus"] = round(coverage * 0.8, 4)
        result["final_score"] = round(result["final_score"] + (coverage * 0.8), 4)

    scored.sort(key=lambda item: item["final_score"], reverse=True)
    if DEBUG and scored:
        print(f"[PIPELINE] total_paths={len(unique_paths)}")
        print(f"[PIPELINE] best_path={scored[0]['path']} score={scored[0]['final_score']}")
        print(f"[PIPELINE] top3={[{'path': s['path'], 'score': s['final_score']} for s in scored[:3]]}")

    return scored[0]
