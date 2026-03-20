from itertools import combinations

from .graph_builder import get_join_paths
from .path_scorer import score_all_paths
from .rag import find_similar_query, load_store
from .schema_linker import get_relevant_tables


def score_relevant_table_coverage(path: list[str], relevant_tables: list[str]) -> float:
    relevant_set = set(relevant_tables)
    path_set = set(path)

    overlap = len(relevant_set.intersection(path_set))
    irrelevant = len(path_set - relevant_set)

    coverage = overlap / max(1, len(relevant_set))
    penalty = irrelevant * 0.2
    return max(0.0, coverage - penalty)


def run_pipeline(query: str, schema: dict, graph) -> dict | None:
    store = load_store()
    rag_match, _ = find_similar_query(query, store, schema)
    if rag_match:
        return rag_match.get("best_path")

    relevant_tables = get_relevant_tables(query, schema, top_k=5)

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
        return None

    scored = score_all_paths(query, unique_paths, schema)

    for result in scored:
        coverage = score_relevant_table_coverage(result["path"], relevant_tables)
        result["final_score"] = result["final_score"] + (coverage * 0.8)

    scored.sort(key=lambda item: item["final_score"], reverse=True)
    return scored[0]
