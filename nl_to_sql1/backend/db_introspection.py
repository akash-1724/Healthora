import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def introspect_database(host, port, database, user, password):
    conn = psycopg2.connect(
        host=host, port=port, database=database, user=user, password=password
    )
    cursor = conn.cursor()

    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """)
    tables = [row[0] for row in cursor.fetchall()]

    schema = {}
    for table in tables:
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        columns = [
            {"name": row[0], "type": row[1], "nullable": row[2]}
            for row in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT kcu.column_name, ccu.table_name, ccu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = %s
        """, (table,))
        foreign_keys = [
            {"column": row[0], "references_table": row[1], "references_column": row[2]}
            for row in cursor.fetchall()
        ]

        schema[table] = {"columns": columns, "foreign_keys": foreign_keys}

    cursor.close()
    conn.close()

    print(f"Successfully introspected {len(schema)} tables.")
    return schema


if __name__ == "__main__":
    schema = introspect_database(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    for table, info in schema.items():
        print(f"\n[{table}]")
        print(f"  Columns: {', '.join(c['name'] for c in info['columns'])}")
        for fk in info["foreign_keys"]:
            print(f"  FK: {fk['column']} -> {fk['references_table']}({fk['references_column']})")