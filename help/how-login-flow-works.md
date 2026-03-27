# How Login + JWT Works (Simple)

Think of JWT like a temporary hospital pass card.

1. User types username and password.
2. Frontend sends `POST /api/login`.
3. Backend checks password:
   - bcrypt hash for modern passwords
   - legacy plain text support only for migration
4. If correct, backend creates JWT token.
5. Token includes username (`sub`) and role.
6. Frontend saves token.
7. Every protected request sends:
   - `Authorization: Bearer <token>`
8. Backend verifies token signature and expiry.
9. Backend checks permission (RBAC) before giving data.

Extra safety:

- Too many wrong logins can lock account for some minutes.
