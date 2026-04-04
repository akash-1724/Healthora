import os
import re

import sqlparse
from groq import Groq
from sqlalchemy import text
from sqlalchemy.orm import Session

from .rag import save_successful_query


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


def is_safe_sql(sql: str) -> tuple[bool, str]:
    parsed = sqlparse.parse(sql)
    if not parsed:
        return False, "Empty query"
    if len(parsed) != 1:
        return False, "Only one SQL statement is allowed"

    statement = parsed[0]
    if statement.get_type() != "SELECT":
        return False, f"Only SELECT allowed, got: {statement.get_type()}"

    dangerous = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        "GRANT",
        "REVOKE",
    ]
    upper = sql.upper()
    for word in dangerous:
        if re.search(rf"\b{word}\b", upper):
            return False, f"Dangerous keyword found: {word}"

    return True, "OK"


def _ensure_limit(sql: str, max_rows: int) -> str:
    if max_rows <= 0:
        return sql.strip()

    limit_match = re.search(r"\bLIMIT\s+(\d+)\s*;?\s*$", sql, flags=re.IGNORECASE)
    if limit_match:
        existing = int(limit_match.group(1))
        if existing <= max_rows:
            return sql.strip()
        return re.sub(
            r"\bLIMIT\s+\d+\s*;?\s*$", f"LIMIT {max_rows}", sql, flags=re.IGNORECASE
        ).strip()
    return sql.rstrip(" ;") + f" LIMIT {max_rows}"


def fix_sql_with_llm(
    original_query: str, bad_sql: str, error_message: str, schema: dict, best_path: dict
) -> str:
    table_context = []
    for table, table_info in schema.items():
        columns = [col["name"] for col in table_info["columns"]]
        marker = " (in selected path)" if table in best_path.get("path", []) else ""
        table_context.append(f"{table}{marker}: {', '.join(columns)}")
    context_text = "\n".join(table_context)

    prompt = f"""You are a PostgreSQL expert. Fix this SQL query.
Original question: {original_query}
Broken SQL:
{bad_sql}
Error:
{error_message}
Available tables and columns:
{context_text}

Rules:
- Use ONLY listed tables/columns.
- Return only corrected SQL.
- SELECT only.
"""

    client = _get_client()
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    fixed_sql = _strip_code_block(response.choices[0].message.content)
    return fixed_sql.strip()


def execute_with_retry(
    db: Session,
    original_query: str,
    sql: str,
    schema: dict,
    best_path: dict,
    max_attempts: int = 3,
) -> dict:
    max_rows = int(os.getenv("AI_QUERY_MAX_ROWS", "500"))
    current_sql = _ensure_limit(sql, max_rows)
    timeout_ms = int(os.getenv("AI_SQL_TIMEOUT_MS", "8000"))
    last_error = None
    relation_missing = None

    def _extract_missing_relation(error_text: str | None) -> str | None:
        if not error_text:
            return None
        match = re.search(
            r'relation\s+"([^"]+)"\s+does\s+not\s+exist',
            error_text,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1)
        return None

    for attempt in range(1, max_attempts + 1):
        safe, reason = is_safe_sql(current_sql)
        if not safe:
            if attempt >= max_attempts:
                return {"success": False, "error": reason, "technical_error": reason}
            current_sql = fix_sql_with_llm(
                original_query, current_sql, reason, schema, best_path
            )
            current_sql = _ensure_limit(current_sql, max_rows)
            continue

        try:
            db.execute(text(f"SET LOCAL statement_timeout = {timeout_ms}"))
            result = db.execute(text(current_sql))
            columns = list(result.keys())
            rows = result.fetchall()

            save_successful_query(
                original_query, best_path, current_sql, len(rows), schema
            )
            return {
                "success": True,
                "columns": columns,
                "rows": rows,
                "count": len(rows),
                "sql": current_sql,
            }
        except Exception as exc:
            last_error = str(exc)
            relation_missing = _extract_missing_relation(last_error)
            if attempt >= max_attempts:
                break
            current_sql = fix_sql_with_llm(
                original_query, current_sql, last_error, schema, best_path
            )
            current_sql = _ensure_limit(current_sql, max_rows)

    return {
        "success": False,
        "error": "Could not process your query after multiple attempts.",
        "technical_error": last_error,
        "error_type": "relation_missing" if relation_missing else "execution_failed",
        "missing_relation": relation_missing,
    }
