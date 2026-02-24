# File: `frontend/src/api.js`

Small API helper for frontend.

- Stores backend base URL from env (`VITE_API_BASE_URL`).
- Adds Bearer token from localStorage automatically.
- Exposes methods for:
  - auth (`login`, `me`)
  - dashboard data (`dashboardSummary`, `dashboardExpiry`, `dashboardNotifications`, `dashboardAccess`)
  - admin user management (`getUsers`, `createUser`, `getRoles`)
  - inventory/patient data (`getInventory`, `getPatients`)
  - AI report stub (`aiReport`)

This keeps page files short and clean.
