# Alembic (Simple)

Alembic is the database change notebook.

## Why we use it

- Database structure changes over time.
- We save each change as a migration file.
- Everyone can apply same changes in same order.

## How it works

1. A new migration file is created in `backend/alembic/versions/`.
2. File says what to change (create table, add column, etc.).
3. We run `alembic upgrade head`.
4. Database moves to newest version safely.

## Easy example

- Old DB has no `patients` table.
- Migration adds `patients` table.
- After upgrade, app can store patient data.

## Important folders

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/`
