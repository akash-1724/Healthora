# File: `backend/users.py`

Users API routes.

Endpoints:

- `GET /api/roles`: list all role options.
- `GET /api/departments`: list department options.
- `GET /api/users`: list users.
- `POST /api/users`: create a new user.
- `PUT /api/users/{user_id}`: edit role/department/status.
- `PATCH /api/users/{user_id}/deactivate`: set user inactive.
- `PATCH /api/users/{user_id}/reset-password`: update password.
- `DELETE /api/users/{user_id}`: remove user (except self).

RBAC:

- All endpoints require `manage_users` permission (system_admin).

Validation:

- Prevents duplicate usernames.
- Validates `role_id` before user creation.
