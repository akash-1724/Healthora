# How AI Report Works (Simple)

Think of this feature as a smart SQL helper.

## What user does

1. User types a question in normal language.
2. Example: "Show top 10 medicines by usage."

## What backend does

1. Understands keywords (medicine, usage, stock, supplier).
2. Picks likely tables and joins.
3. Builds SQL query.
4. Runs SQL on PostgreSQL.
5. Returns rows and summary to frontend.

## Main AI pipeline idea

- Schema linker: finds best tables/columns for the question.
- Path scorer: picks best join path between tables.
- SQL generator: writes SQL with safety rules.
- SQL executor: runs SQL and returns results.

## RAG memory (simple)

- If similar question was solved before, system can reuse helpful context.
- This can improve speed and consistency.

## Safety notes

- Backend still controls execution.
- Role permissions still apply.
- SQL can be shown/hidden in UI when needed.
