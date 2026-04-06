import os
from itertools import combinations

import networkx as nx

from .graph_builder import get_join_paths
from .path_scorer import score_all_paths
from .rag import find_similar_query, load_store
from .schema_linker import get_relevant_tables

DEBUG = os.getenv("AI_DEBUG_NL2SQL", "false").strip().lower() == "true"
TOP_K_TABLES = int(os.getenv("AI_LINKER_TOP_K", "10"))
MAX_PATH_CANDIDATES = int(os.getenv("AI_MAX_PATH_CANDIDATES", "5"))
STEINER_MIN_TERMINALS = int(os.getenv("AI_STEINER_MIN_TERMINALS", "3"))

JOIN_INTENT_KEYWORDS = {
    "join",
    "between",
    "with",
    "across",
    "by",
    "per",
    "from",
    "vs",
    "versus",
    "compared",
    "compare",
}


def score_relevant_table_coverage(path: list[str], relevant_tables: list[str]) -> float:
    relevant_set = set(relevant_tables)
    path_set = set(path)

    overlap = len(relevant_set.intersection(path_set))
    irrelevant = len(path_set - relevant_set)

    coverage = overlap / max(1, len(relevant_set))
    penalty = irrelevant * 0.2
    return max(0.0, coverage - penalty)


def _expand_tables_one_hop(tables: list[str], graph) -> list[str]:
    expanded = list(tables)
    seen = set(expanded)
    undirected = graph.to_undirected()
    for table in tables:
        if table not in undirected:
            continue
        for neighbor in undirected.neighbors(table):
            if neighbor in seen:
                continue
            seen.add(neighbor)
            expanded.append(neighbor)
    return expanded


def _looks_like_multi_table_query(query: str) -> bool:
    tokens = set((query or "").lower().replace("_", " ").split())
    return bool(tokens.intersection(JOIN_INTENT_KEYWORDS))


def _get_steiner_paths(graph, terminals: list[str]) -> list[list[str]]:
    if len(terminals) < STEINER_MIN_TERMINALS:
        return []

    undirected = graph.to_undirected()
    valid = [table for table in terminals if table in undirected]
    if len(valid) < STEINER_MIN_TERMINALS:
        return []

    try:
        tree = nx.algorithms.approximation.steinertree.steiner_tree(undirected, valid)
    except Exception:
        return []

    if tree.number_of_nodes() == 0:
        return []

    candidates: list[list[str]] = []
    cutoff = int(os.getenv("AI_JOIN_PATH_CUTOFF", "6"))
    for start, end in combinations(valid, 2):
        if start not in tree or end not in tree:
            continue
        try:
            path = nx.shortest_path(tree, start, end)
        except nx.NetworkXNoPath:
            continue
        if len(path) - 1 <= cutoff:
            candidates.append(path)
    return candidates


def run_pipeline(
    query: str,
    schema: dict,
    graph,
    exclude_tables: set[str] | None = None,
    return_candidates: bool = False,
):
    excluded = exclude_tables or set()
    if DEBUG:
        print("=" * 70)
        print(f"[PIPELINE] query={query}")

    store = load_store()
    rag_match, rag_score = find_similar_query(query, store, schema)
    if rag_match and not excluded.intersection(
        set(rag_match.get("best_path", {}).get("path", []))
    ):
        if DEBUG:
            print(
                f"[PIPELINE] rag_hit score={rag_score:.4f} path={rag_match.get('best_path', {}).get('path', [])}"
            )
        if return_candidates:
            return [rag_match.get("best_path")]
        return rag_match.get("best_path")

    relevant_tables = get_relevant_tables(query, schema, top_k=TOP_K_TABLES)
    relevant_tables = [table for table in relevant_tables if table not in excluded]

    if len(relevant_tables) == 1 and not _looks_like_multi_table_query(query):
        single = [relevant_tables[0]]
        scored_single = score_all_paths(query, [single], schema)
        if not scored_single:
            return [] if return_candidates else None
        if return_candidates:
            return scored_single[:MAX_PATH_CANDIDATES]
        return scored_single[0]

    expanded_tables = _expand_tables_one_hop(relevant_tables, graph)
    expanded_tables = [table for table in expanded_tables if table not in excluded]
    steiner_paths = _get_steiner_paths(graph, relevant_tables)
    if DEBUG:
        print(f"[PIPELINE] relevant_tables={relevant_tables}")
        print(f"[PIPELINE] expanded_tables={expanded_tables}")
        print(f"[PIPELINE] steiner_paths={len(steiner_paths)}")

    all_paths = list(steiner_paths)
    if len(all_paths) < 2:
        for start, end in combinations(expanded_tables, 2):
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
        return [] if return_candidates else None

    if relevant_tables:
        relevant_set = set(relevant_tables)
        unique_paths = [
            path for path in unique_paths if relevant_set.intersection(path)
        ]
        if not unique_paths:
            return [] if return_candidates else None

    scored = score_all_paths(query, unique_paths, schema)

    for result in scored:
        coverage = score_relevant_table_coverage(result["path"], relevant_tables)
        result["coverage_bonus"] = round(coverage * 0.8, 4)
        result["final_score"] = round(result["final_score"] + (coverage * 0.8), 4)

    scored.sort(key=lambda item: item["final_score"], reverse=True)
    top_scored = scored[:MAX_PATH_CANDIDATES]
    if DEBUG and scored:
        print(f"[PIPELINE] total_paths={len(unique_paths)}")
        print(
            f"[PIPELINE] best_path={top_scored[0]['path']} score={top_scored[0]['final_score']}"
        )
        print(
            f"[PIPELINE] top3={[{'path': s['path'], 'score': s['final_score']} for s in top_scored[:3]]}"
        )

    if return_candidates:
        return top_scored
    return top_scored[0] if top_scored else None
