# File: `backend/security.py`

JWT utility module.

Functions:

- `create_access_token(subject, role)`
- `decode_token(token)`

Environment variables used:

- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_EXPIRE_MINUTES`
