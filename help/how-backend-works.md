# How Backend Works

1. FastAPI starts from `backend/main.py`.
2. Alembic applies migrations (`alembic upgrade head`).
3. Startup seed inserts roles, users, patients, drugs, and batches.
   - Core data is sourced from `HIS (1).xlsx` sheets and normalized to current RBAC roles.
4. Login endpoint validates plain text username/password.
5. On success, backend returns JWT token.
6. Protected APIs use Bearer JWT + RBAC role checks.

Main endpoints:

- `POST /api/login`
- `GET /api/me`
- `GET /api/dashboard-access`
- `GET /api/dashboard-summary`
- `GET /api/dashboard-expiry`
- `GET /api/dashboard-notifications`
- `GET /api/users`
- `POST /api/users`
- `PUT /api/users/{user_id}`
- `PATCH /api/users/{user_id}/deactivate`
- `PATCH /api/users/{user_id}/reset-password`
- `DELETE /api/users/{user_id}`
- `GET /api/departments`
- `GET /api/inventory`
- `PUT /api/inventory/{batch_id}`
- `GET /api/drugs`
- `POST /api/drugs`
- `PUT /api/drugs/{drug_id}`
- `PATCH /api/drugs/{drug_id}/disable`
- `POST /api/drug-batches`
- `PATCH /api/drug-batches/{batch_id}/mark-expired`
- `GET /api/patients`
- `POST /api/patients`
- `PUT /api/patients/{patient_id}`
- `PATCH /api/patients/{patient_id}/archive`
- `GET /api/ai-report`
