from db_introspection import introspect_database
from graph_builder import build_graph, get_join_paths
from path_scorer import score_all_paths
from schema_linker import get_relevant_tables
from rag import find_similar_query, load_store
import os
from dotenv import load_dotenv
from itertools import combinations

load_dotenv()

def score_relevant_table_coverage(path, relevant_tables):
    relevant_set = set(relevant_tables)
    path_set = set(path)

    overlap = len(relevant_set.intersection(path_set))
    irrelevant = len(path_set - relevant_set)

    coverage = overlap / len(relevant_set)
    penalty = irrelevant * 0.2

    return max(0, coverage - penalty)


def run_pipeline(query, schema, G):
    print(f"\n{'='*50}")
    print(f"Query: {query}")
    print(f"{'='*50}")

    # RAG check first
    store = load_store()
    rag_match, rag_score = find_similar_query(query, store, schema)
    if rag_match:
        print(f"[RAG] Reusing cached path — skipping full pipeline")
        return rag_match["best_path"]

    # Step 1: Find relevant tables
    relevant_tables = get_relevant_tables(query, schema, top_k=5)
    print(f"\nRelevant tables: {relevant_tables}")

    # Step 2: Find all paths between relevant tables
    all_paths = []
    for start, end in combinations(relevant_tables, 2):
        paths = get_join_paths(G, start, end)
        all_paths.extend(paths)

    # Remove duplicates
    unique_paths = []
    seen = set()
    for path in all_paths:
        key = tuple(path)
        if key not in seen:
            seen.add(key)
            unique_paths.append(path)

    print(f"\nTotal unique paths found: {len(unique_paths)}")

    if not unique_paths:
        print("No paths found between relevant tables.")
        return None

    # Step 3: Score all paths
    scored = score_all_paths(query, unique_paths, G, schema)

    # Step 4: Re-rank by relevant table coverage
    for result in scored:
        coverage = score_relevant_table_coverage(result["path"], relevant_tables)
        result["final_score"] = result["final_score"] + (coverage * 0.8)

    scored.sort(key=lambda x: x["final_score"], reverse=True)

    best = scored[0]
    print(f"\nBest path: {' → '.join(best['path'])}")
    print(f"Score: {best['final_score']}")

    return best


if __name__ == "__main__":
    schema = introspect_database(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    G = build_graph(schema)

    queries = [
        "show me drugs prescribed to a patient",
        "which user dispensed the medicine with drug id 5",
        "show me all purchase orders from a supplier",
    ]

    for query in queries:
        result = run_pipeline(query, schema, G)