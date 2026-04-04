import os

from groq import Groq
from sqlalchemy import text


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


def _collect_data_hints(best_path: dict, schema: dict, db) -> str:
    hints: list[str] = []
    for table in best_path.get("path", []):
        if table not in schema:
            continue
        safe_table = quote_table_name(table)
        try:
            sample_rows = (
                db.execute(text(f"SELECT * FROM {safe_table} LIMIT 2")).mappings().all()
            )
            if sample_rows:
                hints.append(f"Sample {safe_table}: {sample_rows}")
        except Exception:
            continue

        text_cols = [
            col["name"]
            for col in schema[table].get("columns", [])
            if isinstance(col.get("type"), str)
            and any(
                token in col["type"].lower() for token in ("char", "text", "varchar")
            )
        ]
        for col in text_cols[:3]:
            try:
                distinct_rows = (
                    db.execute(
                        text(
                            f"SELECT DISTINCT {col} AS v FROM {safe_table} "
                            f"WHERE {col} IS NOT NULL LIMIT 12"
                        )
                    )
                    .mappings()
                    .all()
                )
                values = [
                    row.get("v")
                    for row in distinct_rows
                    if row.get("v") not in (None, "")
                ]
                if values and len(values) <= 12:
                    hints.append(f"Distinct values {safe_table}.{col}: {values}")
            except Exception:
                continue

        date_cols = [
            col["name"]
            for col in schema[table].get("columns", [])
            if isinstance(col.get("type"), str)
            and any(token in col["type"].lower() for token in ("date", "time"))
        ]
        for col in date_cols[:2]:
            try:
                range_row = (
                    db.execute(
                        text(
                            f"SELECT MIN({col}) AS min_v, MAX({col}) AS max_v FROM {safe_table}"
                        )
                    )
                    .mappings()
                    .first()
                )
                if range_row and (
                    range_row.get("min_v") is not None
                    or range_row.get("max_v") is not None
                ):
                    hints.append(
                        f"Date range {safe_table}.{col}: {range_row.get('min_v')} to {range_row.get('max_v')}"
                    )
            except Exception:
                continue

    return "\n".join(hints)


def generate_sql(
    query: str,
    best_path: dict,
    schema: dict,
    graph,
    db,
    alternative_paths: list[dict] | None = None,
) -> str:
    context_text, join_conditions = build_context(best_path, schema, graph)
    data_hints = _collect_data_hints(best_path, schema, db)
    joins_text = "\n".join(join_conditions)
    alternatives = alternative_paths or []
    alt_text = (
        "\n".join(f"- {' -> '.join(path.get('path', []))}" for path in alternatives[:2])
        or "- none"
    )
    preferred_family = os.getenv("AI_SCHEMA_FAMILY", "legacy").strip().lower()

    prompt = f"""You are a PostgreSQL expert. Generate one SQL SELECT query.

Tables and columns available:
{context_text}

Join conditions to use:
{joins_text}

Data hints (real values/ranges):
{data_hints}

Alternative join options if first path is weak:
{alt_text}

User question: {query}

Rules:
- Use ONLY the listed tables and columns.
- Use the exact join conditions provided.
- Return ONLY SQL, no explanation.
- Use SELECT only.
- Prefer {preferred_family} schema family tables when possible.
- If user asks about sales or revenue, prioritize dispensing_records + drug_batches + drugs and date filter on dispensing_records.dispensed_at.
- If user asks about stock/expiry, prioritize drug_batches and filter on expiry_date/is_expired where relevant.
- For drug-name searches, use case-insensitive matching with ILIKE and prefer `(d.drug_name ILIKE '%name%' OR d.generic_name ILIKE '%name%')` instead of strict equality.
- drug_id and batch_id are different fields. If user asks for drug id, filter on drug_id not batch_id.
- If path contains dispense_item without drug/drugs table, bridge via drug_batch (dispense_item.batch_id = drug_batch.batch_id).
- Respect exact table casing for special names like "User".
- Use enum values exactly from Data hints when filtering status/type columns.
"""

    client = _get_client()
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return _strip_code_block(response.choices[0].message.content).strip()
