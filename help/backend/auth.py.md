# File: `backend/auth.py`

Contains simple authentication logic.

- `login_user(...)`: checks username/password, creates UUID token, stores token in DB.
- `get_current_user(...)`: reads `Authorization: Bearer <token>`, validates token, returns user.

Libraries:

- `uuid` for token generation.
- FastAPI `HTTPException` for simple error responses.
