# File: `backend/database.py`

Database setup module.

- Reads `DATABASE_URL` from env.
- Creates SQLAlchemy `engine` with `pool_pre_ping=True`.
- Creates `SessionLocal` for DB sessions.
- Creates `Base` for models.
- `get_db()` opens and closes DB session per request.
