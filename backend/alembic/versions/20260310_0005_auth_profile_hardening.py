"""Add auth hardening and user profile fields

Revision ID: 20260310_0005
Revises: 20260310_0004
Create Date: 2026-03-10 23:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260310_0005"
down_revision: Union[str, Sequence[str], None] = "20260310_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    user_cols = {col["name"] for col in inspector.get_columns("users")}

    if "full_name" not in user_cols:
        op.add_column("users", sa.Column("full_name", sa.String(length=150), nullable=True))
    if "email" not in user_cols:
        op.add_column("users", sa.Column("email", sa.String(length=150), nullable=True))
    if "phone" not in user_cols:
        op.add_column("users", sa.Column("phone", sa.String(length=40), nullable=True))
    if "failed_login_count" not in user_cols:
        op.add_column("users", sa.Column("failed_login_count", sa.Integer(), nullable=True))
        op.execute("UPDATE users SET failed_login_count=0 WHERE failed_login_count IS NULL")
        op.alter_column("users", "failed_login_count", existing_type=sa.Integer(), nullable=False)
    if "locked_until" not in user_cols:
        op.add_column("users", sa.Column("locked_until", sa.DateTime(), nullable=True))
    if "last_login_at" not in user_cols:
        op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))
    if "password_changed_at" not in user_cols:
        op.add_column("users", sa.Column("password_changed_at", sa.DateTime(), nullable=True))
    if "must_reset_password" not in user_cols:
        op.add_column("users", sa.Column("must_reset_password", sa.Boolean(), nullable=True))
        op.execute("UPDATE users SET must_reset_password=FALSE WHERE must_reset_password IS NULL")
        op.alter_column("users", "must_reset_password", existing_type=sa.Boolean(), nullable=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    user_cols = {col["name"] for col in inspector.get_columns("users")}

    for col in [
        "must_reset_password",
        "password_changed_at",
        "last_login_at",
        "locked_until",
        "failed_login_count",
        "phone",
        "email",
        "full_name",
    ]:
        if col in user_cols:
            op.drop_column("users", col)
