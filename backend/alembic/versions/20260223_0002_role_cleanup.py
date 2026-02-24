"""normalize role values for final rbac matrix

Revision ID: 20260223_0002
Revises: 20260223_0001
Create Date: 2026-02-23 01:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260223_0002"
down_revision: Union[str, Sequence[str], None] = "20260223_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            INSERT INTO roles (name, display_name)
            SELECT 'system_admin', 'System Admin'
            WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name='system_admin')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO roles (name, display_name)
            SELECT 'chief_medical_officer', 'Chief Medical Officer'
            WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name='chief_medical_officer')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO roles (name, display_name)
            SELECT 'pharmacy_manager', 'Pharmacy Manager'
            WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name='pharmacy_manager')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO roles (name, display_name)
            SELECT 'senior_pharmacist', 'Senior Pharmacist'
            WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name='senior_pharmacist')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO roles (name, display_name)
            SELECT 'staff_pharmacist', 'Staff Pharmacist'
            WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name='staff_pharmacist')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO roles (name, display_name)
            SELECT 'inventory_clerk', 'Inventory Clerk'
            WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name='inventory_clerk')
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE users
            SET role_id = (SELECT id FROM roles WHERE name='system_admin' LIMIT 1)
            WHERE role_id IN (SELECT id FROM roles WHERE name='admin')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE users
            SET role_id = (SELECT id FROM roles WHERE name='chief_medical_officer' LIMIT 1)
            WHERE role_id IN (SELECT id FROM roles WHERE name='doctor')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE users
            SET role_id = (SELECT id FROM roles WHERE name='staff_pharmacist' LIMIT 1)
            WHERE role_id IN (SELECT id FROM roles WHERE name='pharmacist')
            """
        )
    )

    conn.execute(sa.text("DELETE FROM roles WHERE name IN ('admin', 'doctor', 'pharmacist')"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE roles SET name='admin', display_name='System Admin' WHERE name='system_admin'"))
