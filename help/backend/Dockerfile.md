# File: `backend/Dockerfile`

Builds backend container.

Steps:

1. Start from `python:3.11-slim`
2. Install Poetry
3. Install dependencies from `pyproject.toml`
4. Copy backend files
5. Run `uvicorn main:app` on port `8000`
