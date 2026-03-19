import psycopg2
import sqlparse
import os
from dotenv import load_dotenv
from groq import Groq
from rag import save_successful_query

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def is_safe_sql(sql):
    parsed = sqlparse.parse(sql)
    if not parsed:
        return False, "Empty query"
    statement = parsed[0]
    if statement.get_type() != 'SELECT':
        return False, f"Only SELECT allowed, got: {statement.get_type()}"
    dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 'ALTER']
    for word in dangerous:
        if word in sql.upper():
            return False, f"Dangerous keyword found: {word}"
    return True, "OK"


def fix_sql_with_llm(original_query, bad_sql, error_message, schema, best_path):
    table_context = []
    for table in best_path["path"]:
        if table in schema:
            columns = [col["name"] for col in schema[table]["columns"]]
            table_context.append(f"{table}: {', '.join(columns)}")
    context_text = "\n".join(table_context)

    prompt = f"""You are a PostgreSQL expert. The following SQL query has an error.
Original user question: {original_query}
Broken SQL:
{bad_sql}
Error message:
{error_message}
Available tables and their exact columns:
{context_text}
Fix the SQL query. Rules:
- Use ONLY the columns listed above, no others
- Return ONLY the corrected SQL, no explanation
- Always use SELECT
- Use proper PostgreSQL syntax
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    fixed_sql = response.choices[0].message.content.strip()
    if fixed_sql.startswith("```"):
        fixed_sql = fixed_sql.split("```")[1]
        if fixed_sql.startswith("sql"):
            fixed_sql = fixed_sql[3:]
    return fixed_sql.strip()


def execute_with_retry(original_query, sql, schema, best_path, max_attempts=3):
    current_sql = sql
    last_error = None

    for attempt in range(1, max_attempts + 1):
        print(f"\nAttempt {attempt}:")
        print(f"SQL: {current_sql}")

        safe, reason = is_safe_sql(current_sql)
        if not safe:
            print(f"Safety check failed: {reason}")
            current_sql = fix_sql_with_llm(original_query, current_sql, reason, schema, best_path)
            continue

        try:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD")
            )
            cursor = conn.cursor()
            cursor.execute(current_sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            print(f"✅ Success on attempt {attempt}")

            save_successful_query(original_query, best_path, current_sql, len(rows), schema)

            return {
                "success": True,
                "columns": columns,
                "rows": rows,
                "count": len(rows),
                "sql": current_sql
            }

        except Exception as e:
            last_error = str(e)
            print(f"❌ Execution failed: {last_error}")
            if attempt < max_attempts:
                print(f"Fixing SQL...")
                current_sql = fix_sql_with_llm(original_query, current_sql, last_error, schema, best_path)

    return {
        "success": False,
        "error": "Could not process your query after multiple attempts.",
        "technical_error": last_error
    }


if __name__ == "__main__":
    from db_introspection import introspect_database
    from graph_builder import build_graph
    from pipeline import run_pipeline
    from sql_generator import generate_sql

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
        print(f"{'='*50}")
        best_path = run_pipeline(query, schema, G)
        sql = generate_sql(query, best_path, schema, G)
        result = execute_with_retry(query, sql, schema, best_path)

        if result["success"]:
            print(f"\nColumns: {result['columns']}")
            print(f"Rows returned: {result['count']}")
            if result['rows']:
                for row in result['rows'][:3]:
                    print(f"  {row}")
        else:
            print(f"\nFailed: {result['error']}")