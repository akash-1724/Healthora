# File: `backend/main.py`

Main FastAPI bootstrap file.

Responsibilities:

- Creates app and CORS configuration.
- Runs seed routine on startup (`seed_all`).
- Registers routers:
  - auth routes (`/api/login`, `/api/me`)
  - user management routes
  - inventory/data routes
  - dashboard routes

Note:

- Database schema creation is handled by Alembic migrations, not `create_all`.
