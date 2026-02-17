# How Backend Works

1. FastAPI starts from `backend/main.py`.
2. SQLAlchemy creates DB tables from `backend/models.py`.
3. Seed runs once and creates:
   - role `admin`
   - user `admin/admin123`
4. Login endpoint checks plain text username/password.
5. On success, backend generates UUID token and stores it in `tokens` table.
6. Protected APIs read `Authorization: Bearer <token>` and validate token from DB.

Main endpoints:

- `POST /api/login`
- `GET /api/me`
- `GET /api/users`
- `POST /api/users`
- `GET /api/inventory`
