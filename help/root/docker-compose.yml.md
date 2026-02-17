# File: `docker-compose.yml`

Runs all containers with one command.

Services:

- `postgres`: PostgreSQL database (container `5432`, host default `5433`).
- `backend`: FastAPI app (port `8000`).
- `frontend`: Vite React app (port `3000`).

Important points:

- Backend waits for postgres using `depends_on`.
- Frontend waits for backend using `depends_on`.
- Volume `postgres_data` stores DB data persistently.
- Postgres host port is configurable with `POSTGRES_HOST_PORT` to avoid local port conflicts.
