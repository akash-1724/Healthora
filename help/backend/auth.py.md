# File: `backend/auth.py`

Authentication routes with JWT.

Endpoints:

- `POST /api/login`:
  - validates plain text username/password
  - returns JWT bearer token
- `GET /api/me`:
  - validates Bearer token
  - returns current user profile and role

Libraries:

- FastAPI routing + dependency injection.
- JWT helper from `security.py`.
