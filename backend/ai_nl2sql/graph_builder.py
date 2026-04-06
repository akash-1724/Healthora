import networkx as nx
import os


def _build_shortest_path_cache(
    graph: nx.DiGraph, max_hops: int
) -> dict[tuple[str, str], list[str]]:
    cache: dict[tuple[str, str], list[str]] = {}
    undirected = graph.to_undirected()
    for source, targets in nx.all_pairs_shortest_path(undirected):
        for target, path in targets.items():
            if source == target:
                continue
            if len(path) - 1 > max_hops:
                continue
            cache[(source, target)] = path
    return cache


def build_graph(schema: dict) -> nx.DiGraph:
    graph = nx.DiGraph()

    for table, info in schema.items():
        graph.add_node(table, columns=info["columns"])

    for table, info in schema.items():
        for fk in info["foreign_keys"]:
            graph.add_edge(
                table,
                fk["references_table"],
                from_column=fk["column"],
                to_column=fk["references_column"],
            )

    cutoff = int(os.getenv("AI_JOIN_PATH_CUTOFF", "6"))
    graph.graph["shortest_path_cache"] = _build_shortest_path_cache(graph, cutoff)

    return graph


def get_join_paths(
    graph: nx.DiGraph, start_table: str, end_table: str
) -> list[list[str]]:
    cutoff = int(os.getenv("AI_JOIN_PATH_CUTOFF", "6"))
    cache = graph.graph.get("shortest_path_cache", {})
    cached = cache.get((start_table, end_table))
    if cached:
        return [cached]

    try:
        return list(
            nx.all_simple_paths(
                graph.to_undirected(), start_table, end_table, cutoff=cutoff
            )
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []
