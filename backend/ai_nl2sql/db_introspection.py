from sqlalchemy import inspect

from database import engine


def introspect_database() -> dict:
    inspector = inspect(engine)
    schema = {}

    for table in inspector.get_table_names(schema="public"):
        columns = []
        for row in inspector.get_columns(table, schema="public"):
            columns.append(
                {
                    "name": row["name"],
                    "type": str(row["type"]),
                    "nullable": "YES" if row.get("nullable", True) else "NO",
                }
            )

        foreign_keys = []
        for fk in inspector.get_foreign_keys(table, schema="public"):
            constrained = fk.get("constrained_columns") or []
            referred = fk.get("referred_columns") or []
            ref_table = fk.get("referred_table")
            for from_col, to_col in zip(constrained, referred):
                foreign_keys.append(
                    {
                        "column": from_col,
                        "references_table": ref_table,
                        "references_column": to_col,
                    }
                )

        schema[table] = {"columns": columns, "foreign_keys": foreign_keys}

    return schema
