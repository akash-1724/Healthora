# File: `frontend/src/Users.jsx`

Users page with basic CRUD subset.

Features:

- Tries to load users with `GET /api/users`.
- Falls back to sample local users if API fails.
- Shows users list (`admin` and added users).
- Add user form with `username`, `password`, `role_id`.
- Buttons are MVP-friendly and simple.

UI style:

- Basic inline CSS only.
