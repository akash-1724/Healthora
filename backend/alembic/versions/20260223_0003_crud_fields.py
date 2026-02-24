"""add columns for advanced user, patient, and inventory actions

Revision ID: 20260223_0003
Revises: 20260223_0002
Create Date: 2026-02-23 22:50:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260223_0003"
down_revision: Union[str, Sequence[str], None] = "20260223_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    user_cols = {col["name"] for col in inspector.get_columns("users")}
    if "department" not in user_cols:
        op.add_column("users", sa.Column("department", sa.String(length=120), nullable=True))
        op.execute("UPDATE users SET department='Pharmacy' WHERE department IS NULL")
        op.alter_column("users", "department", existing_type=sa.String(length=120), nullable=False)

    patient_cols = {col["name"] for col in inspector.get_columns("patients")}
    if "address" not in patient_cols:
        op.add_column("patients", sa.Column("address", sa.String(length=200), nullable=True))
    if "created_by_user_id" not in patient_cols:
        op.add_column("patients", sa.Column("created_by_user_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_patients_created_by_user", "patients", "users", ["created_by_user_id"], ["user_id"])
    if "created_at" not in patient_cols:
        op.add_column("patients", sa.Column("created_at", sa.DateTime(), nullable=True))
        op.execute("UPDATE patients SET created_at=NOW() WHERE created_at IS NULL")
        op.alter_column("patients", "created_at", existing_type=sa.DateTime(), nullable=False)
    if "is_archived" not in patient_cols:
        op.add_column("patients", sa.Column("is_archived", sa.Boolean(), nullable=True))
        op.execute("UPDATE patients SET is_archived=FALSE WHERE is_archived IS NULL")
        op.alter_column("patients", "is_archived", existing_type=sa.Boolean(), nullable=False)

    drug_cols = {col["name"] for col in inspector.get_columns("drugs")}
    if "is_active" not in drug_cols:
        op.add_column("drugs", sa.Column("is_active", sa.Boolean(), nullable=True))
        op.execute("UPDATE drugs SET is_active=TRUE WHERE is_active IS NULL")
        op.alter_column("drugs", "is_active", existing_type=sa.Boolean(), nullable=False)
    if "low_stock_threshold" not in drug_cols:
        op.add_column("drugs", sa.Column("low_stock_threshold", sa.Integer(), nullable=True))
        op.execute("UPDATE drugs SET low_stock_threshold=50 WHERE low_stock_threshold IS NULL")
        op.alter_column("drugs", "low_stock_threshold", existing_type=sa.Integer(), nullable=False)

    batch_cols = {col["name"] for col in inspector.get_columns("drug_batches")}
    if "is_expired" not in batch_cols:
        op.add_column("drug_batches", sa.Column("is_expired", sa.Boolean(), nullable=True))
        op.execute("UPDATE drug_batches SET is_expired=FALSE WHERE is_expired IS NULL")
        op.alter_column("drug_batches", "is_expired", existing_type=sa.Boolean(), nullable=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    batch_cols = {col["name"] for col in inspector.get_columns("drug_batches")}
    if "is_expired" in batch_cols:
        op.drop_column("drug_batches", "is_expired")

    drug_cols = {col["name"] for col in inspector.get_columns("drugs")}
    if "low_stock_threshold" in drug_cols:
        op.drop_column("drugs", "low_stock_threshold")
    if "is_active" in drug_cols:
        op.drop_column("drugs", "is_active")

    patient_cols = {col["name"] for col in inspector.get_columns("patients")}
    if "is_archived" in patient_cols:
        op.drop_column("patients", "is_archived")
    if "created_at" in patient_cols:
        op.drop_column("patients", "created_at")
    if "created_by_user_id" in patient_cols:
        op.drop_constraint("fk_patients_created_by_user", "patients", type_="foreignkey")
        op.drop_column("patients", "created_by_user_id")
    if "address" in patient_cols:
        op.drop_column("patients", "address")

    user_cols = {col["name"] for col in inspector.get_columns("users")}
    if "department" in user_cols:
        op.drop_column("users", "department")
