# File: `frontend/src/App.jsx`

Frontend root file.

What it does:

- Sets up React Router routes.
- Defines three main routes:
  - `/` landing page
  - `/login` login page
  - `/dashboard` protected role-based dashboard
- Redirects unknown routes based on auth state.
- Mounts React app into `#root`.

Routes:

- `/` -> Landing
- `/login` -> Login
- `/dashboard` -> Role-based dashboard
