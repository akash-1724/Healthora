# File: `frontend/src/api.js`

Small API helper for frontend.

- Stores backend base URL from env (`VITE_API_BASE_URL`).
- Adds Bearer token from localStorage automatically.
- Has helper methods: login, me, getUsers, createUser, getInventory.

This keeps page files short and clean.
