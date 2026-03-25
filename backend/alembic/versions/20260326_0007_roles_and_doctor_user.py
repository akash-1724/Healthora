"""Add doctor role and normalize clerk naming

Revision ID: 20260326_0007
Revises: 20260325_0006
Create Date: 2026-03-26 00:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260326_0007"
down_revision: Union[str, Sequence[str], None] = "20260325_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "roles" in inspector.get_table_names():
        op.execute("UPDATE roles SET display_name='Clerk' WHERE name='inventory_clerk'")
        op.execute(
            """
            INSERT INTO roles (name, display_name)
            SELECT 'doctor', 'Doctor'
            WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name='doctor')
            """
        )
        if "users" in inspector.get_table_names():
            op.execute(
                """
                INSERT INTO users (
                    username,
                    password,
                    full_name,
                    role_id,
                    department,
                    is_active,
                    failed_login_count,
                    must_reset_password,
                    created_at
                )
                SELECT
                    'doctor1',
                    'doctor123',
                    'Dr. Demo User',
                    r.id,
                    'General Medicine',
                    TRUE,
                    0,
                    FALSE,
                    NOW()
                FROM roles r
                WHERE r.name='doctor'
                AND NOT EXISTS (SELECT 1 FROM users WHERE username='doctor1')
                """
            )

    if "role" in inspector.get_table_names():
        op.execute("UPDATE role SET role_name='Clerk' WHERE lower(role_name)='inventory clerk'")
        op.execute(
            """
            INSERT INTO role (role_id, role_name)
            SELECT COALESCE((SELECT MAX(role_id) + 1 FROM role), 1), 'Doctor'
            WHERE NOT EXISTS (SELECT 1 FROM role WHERE lower(role_name)='doctor')
            """
        )
        op.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('role', 'role_id'),
                COALESCE((SELECT MAX(role_id) FROM role), 1),
                (SELECT COUNT(*) > 0 FROM role)
            )
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "roles" in inspector.get_table_names():
        op.execute("UPDATE roles SET display_name='Inventory Clerk' WHERE name='inventory_clerk'")
        if "users" in inspector.get_table_names():
            op.execute("DELETE FROM users WHERE username='doctor1'")
        op.execute("DELETE FROM roles WHERE name='doctor'")

    if "role" in inspector.get_table_names():
        op.execute("UPDATE role SET role_name='Inventory Clerk' WHERE lower(role_name)='clerk'")
        op.execute("DELETE FROM role WHERE lower(role_name)='doctor'")
