import os

from groq import Groq


def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing")
    return Groq(api_key=api_key)


def _strip_code_block(sql: str) -> str:
    value = (sql or "").strip()
    if not value.startswith("```"):
        return value
    parts = value.split("```")
    if len(parts) < 2:
        return value
    block = parts[1].strip()
    if block.lower().startswith("sql"):
        block = block[3:].strip()
    return block


def quote_table_name(name: str) -> str:
    reserved_words = {
        "user",
        "order",
        "table",
        "select",
        "where",
        "group",
        "index",
        "column",
        "check",
        "default",
        "end",
        "case",
    }
    if name.lower() in reserved_words or name[:1].isupper():
        return f'"{name}"'
    return name


def build_context(best_path: dict, schema: dict, graph) -> tuple[str, list[str]]:
    context = []
    for table in best_path["path"]:
        if table not in schema:
            continue
        columns = schema[table]["columns"]
        details = ", ".join(f"{col['name']} ({col['type']})" for col in columns)
        context.append(f"Table {quote_table_name(table)}: {details}")

    join_conditions = []
    path = best_path["path"]
    for i in range(len(path) - 1):
        left = path[i]
        right = path[i + 1]
        if graph.has_edge(left, right):
            edge = graph[left][right]
            join_conditions.append(
                f"{quote_table_name(left)}.{edge['from_column']} = {quote_table_name(right)}.{edge['to_column']}"
            )
        elif graph.has_edge(right, left):
            edge = graph[right][left]
            join_conditions.append(
                f"{quote_table_name(right)}.{edge['from_column']} = {quote_table_name(left)}.{edge['to_column']}"
            )

    return "\n".join(context), join_conditions


def generate_sql(query: str, best_path: dict, schema: dict, graph) -> str:
    context_text, join_conditions = build_context(best_path, schema, graph)
    joins_text = "\n".join(join_conditions)

    prompt = f"""You are a PostgreSQL expert. Generate one SQL SELECT query.

Tables and columns available:
{context_text}

Join conditions to use:
{joins_text}

User question: {query}

Rules:
- Use ONLY the listed tables and columns.
- Use the exact join conditions provided.
- Return ONLY SQL, no explanation.
- Use SELECT only.
- If user asks about sales or revenue, prioritize dispensing_records + drug_batches + drugs and date filter on dispensing_records.dispensed_at.
- If user asks about stock/expiry, prioritize drug_batches and filter on expiry_date/is_expired where relevant.
- For drug-name searches, use case-insensitive matching with ILIKE and prefer `(d.drug_name ILIKE '%name%' OR d.generic_name ILIKE '%name%')` instead of strict equality.
"""

    client = _get_client()
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return _strip_code_block(response.choices[0].message.content).strip()
