import networkx as nx
from db_introspection import introspect_database
import os
from dotenv import load_dotenv

load_dotenv()

def build_graph(schema):
    G = nx.DiGraph()

    for table, info in schema.items():
        G.add_node(table, columns=info["columns"])

    for table, info in schema.items():
        for fk in info["foreign_keys"]:
            G.add_edge(
                table,
                fk["references_table"],
                from_column=fk["column"],
                to_column=fk["references_column"]
            )

    return G

def get_join_paths(G, start_table, end_table):
    try:
        paths = list(nx.all_simple_paths(G.to_undirected(), start_table, end_table, cutoff=4))
        return paths
    except nx.NetworkXNoPath:
        return []
    except nx.NodeNotFound as e:
        print(f"Table not found: {e}")
        return []

def print_graph_info(G):
    print(f"\nTotal Tables (nodes): {G.number_of_nodes()}")
    print(f"Total Relationships (edges): {G.number_of_edges()}")
    print("\nAll Relationships:")
    for edge in G.edges(data=True):
        print(f"  {edge[0]}.{edge[2]['from_column']} → {edge[1]}.{edge[2]['to_column']}")


if __name__ == "__main__":
    schema = introspect_database(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    G = build_graph(schema)
    print_graph_info(G)

    print("\n--- Testing Join Paths ---")
    paths = get_join_paths(G, "patient", "drug")
    print(f"\nPaths from patient → drug:")
    for i, path in enumerate(paths):
        print(f"  Path {i+1}: {' → '.join(path)}")