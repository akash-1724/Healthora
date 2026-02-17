# File: `backend/models.py`

Defines database tables.

Tables:

- `Role`: `id`, `name`
- `User`: `user_id`, `username`, `password`, `role_id`, `is_active`, `created_at`
- `Token`: `id`, `token`, `user_id`

Library used:

- SQLAlchemy ORM (Column, relationship, ForeignKey).

Note:

- Password is plain text by project requirement.
