# File: `backend/deps.py`

Reusable dependency functions.

Includes:

- `get_current_user`: validates Bearer JWT and loads active user.
- `require_permission(permission)`: permission guard used by endpoints.
- `ROLE_PERMISSIONS`: maps each role to permission set.
- `ROLE_MODULES`: maps each role to sidebar modules (`dashboard`, `users`, `patients`, `drugs`, `inventory`, `ai_report`, `settings`).

Why useful:

- Centralized RBAC and module visibility config in one file.
