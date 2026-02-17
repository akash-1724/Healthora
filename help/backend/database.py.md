# File: `backend/database.py`

Simple DB setup file.

- Reads `DATABASE_URL` from env.
- Creates SQLAlchemy `engine`.
- Creates `SessionLocal` for DB sessions.
- Creates `Base` for models.
- `get_db()` opens and closes DB session per request.
