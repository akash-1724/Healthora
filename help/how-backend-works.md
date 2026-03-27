# How Backend Works (Simple)

Think of backend as the hospital brain.

## Big picture

1. App starts from `backend/main.py`.
2. Database tables are kept up-to-date by Alembic migrations.
3. Backend reads real data from PostgreSQL.
4. Users log in and get a JWT token.
5. Every protected API checks token + permissions.

## What happens at startup

1. FastAPI starts routers (auth, users, inventory, AI report, reorder, and more).
2. Optional startup seed runs only if `ENABLE_STARTUP_SEED=true`.
3. A daily background job marks old drug batches as expired.

## Security in one line

- Passwords are checked with bcrypt.
- JWT token is used for API auth.
- RBAC permissions decide who can do what.

## Main API groups

- Auth: login, register sysadmin, current user.
- Users: create/update/deactivate users (with role rules).
- Patients/Prescriptions/Dispensing: patient treatment flow.
- Inventory/Drugs/Batches: stock management.
- Suppliers/Purchase Orders: medicine procurement flow.
- AI Report: ask questions in natural language and run SQL.
- Reorder Recommendation: forecast usage and suggest reorder quantity.
