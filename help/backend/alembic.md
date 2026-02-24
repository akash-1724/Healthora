# Alembic Migration Files

Files added:

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/20260223_0001_rbac_schema.py`

Purpose:

- Manage schema with migrations instead of runtime `create_all`.
- Backend container runs `alembic upgrade head` before starting API.
