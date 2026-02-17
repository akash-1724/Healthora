# File: `backend/main.py`

Backend entry point.

What it does:

- Creates FastAPI app.
- Adds CORS so frontend can call backend.
- Creates tables at startup.
- Seeds role `admin` and user `admin/admin123`.
- Provides `/api/login` and `/api/me` endpoints.
- Includes routers from `users.py` and `inventory.py`.

Ports:

- Runs on `8000` inside container.
