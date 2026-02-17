# File: `frontend/src/Login.jsx`

Simple login page.

- Takes username and password.
- Calls `POST /api/login`.
- Saves returned token in localStorage.
- Saves username in localStorage for profile display.
- Redirects to dashboard on success.

Default credentials to use manually:

- `admin` / `admin123`
