# How Login Flow Works

1. User enters username/password on Login page.
2. Frontend sends `POST /api/login`.
3. Backend verifies plain text credentials from `users` table.
4. Backend creates UUID token and saves in `tokens` table.
5. Backend returns token.
6. Frontend stores token in localStorage.
7. For next API calls, frontend sends `Authorization: Bearer <token>`.
8. Backend validates token and returns requested data.
