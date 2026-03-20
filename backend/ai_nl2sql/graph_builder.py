import networkx as nx


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

    return graph


def get_join_paths(graph: nx.DiGraph, start_table: str, end_table: str) -> list[list[str]]:
    try:
        return list(nx.all_simple_paths(graph.to_undirected(), start_table, end_table, cutoff=4))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []
