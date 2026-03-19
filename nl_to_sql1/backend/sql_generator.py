from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def quote_table_name(name):
    reserved_words = [
        "user", "order", "table", "select", "where", "group",
        "index", "column", "check", "default", "end", "case"
    ]
    if name.lower() in reserved_words or name[0].isupper():
        return f'"{name}"'
    return name

def build_context(best_path, schema, G):
    context = []

    for table in best_path["path"]:
        if table in schema:
            columns = schema[table]["columns"]
            col_details = ", ".join([
                f"{col['name']} ({col['type']})"
                for col in columns
            ])
            quoted = quote_table_name(table)
            context.append(f"Table {quoted}: {col_details}")

    # If dispense_item is in path but drug_batch is not, add it so LLM can bridge drug_id
    path_tables = best_path["path"]
    if "dispense_item" in path_tables and "drug_batch" not in path_tables:
        if "drug_batch" in schema:
            cols = ", ".join([f"{c['name']} ({c['type']})" for c in schema["drug_batch"]["columns"]])
            context.append(f"Table drug_batch (join via dispense_item.batch_id = drug_batch.batch_id): {cols}")

    # Add join conditions from the path
    join_conditions = []
    path = best_path["path"]
    for i in range(len(path) - 1):
        from_table = path[i]
        to_table = path[i + 1]

        if G.has_edge(from_table, to_table):
            edge = G[from_table][to_table]
            join_conditions.append(
                f"{quote_table_name(from_table)}.{edge['from_column']} = {quote_table_name(to_table)}.{edge['to_column']}"
            )
        elif G.has_edge(to_table, from_table):
            edge = G[to_table][from_table]
            join_conditions.append(
                f"{quote_table_name(to_table)}.{edge['from_column']} = {quote_table_name(from_table)}.{edge['to_column']}"
            )

    return "\n".join(context), join_conditions


def generate_sql(query, best_path, schema, G):
    table_context, join_conditions = build_context(best_path, schema, G)
    joins_text = "\n".join(join_conditions)

    prompt = f"""You are a PostgreSQL expert. Generate a SQL SELECT query.

Tables and columns available:
{table_context}

Join conditions to use:
{joins_text}

User question: {query}

Rules:
- Use ONLY the tables and columns listed above
- Use the exact join conditions provided
- Return ONLY the SQL query, no explanation
- Always use SELECT, never DELETE or UPDATE or DROP
- Use table aliases for clarity
- drug_id and batch_id are DIFFERENT columns. When user says "drug id X", filter on drug_id NOT batch_id
- If the path has dispense_item but not drug, join drug_batch first: JOIN drug_batch db ON di.batch_id = db.batch_id, then filter WHERE db.drug_id = X
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    sql = response.choices[0].message.content.strip()
    if sql.startswith("```"):
        sql = sql.split("```")[1]
        if sql.startswith("sql"):
            sql = sql[3:]
    sql = sql.strip()
    return sql


if __name__ == "__main__":
    from db_introspection import introspect_database
    from graph_builder import build_graph
    from pipeline import run_pipeline

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
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        best_path = run_pipeline(query, schema, G)
        if best_path:
            sql = generate_sql(query, best_path, schema, G)
            print(f"\nGenerated SQL:\n{sql}")