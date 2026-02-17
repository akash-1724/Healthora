# File: `frontend/src/App.jsx`

Frontend root file.

What it does:

- Sets up React Router routes.
- Protects dashboard/users/inventory/reorder/reports routes using token from localStorage.
- Shows top navigation bar on every protected page.
- Top bar includes HEALTHORA logo text, Home button, tabs, user name, and Logout.
- Mounts React app into `#root`.

Routes:

- `/` -> Login
- `/dashboard` -> Dashboard
- `/users` -> Users
- `/inventory` -> Inventory
- `/reorder` -> Reorder
- `/reports` -> Reports
