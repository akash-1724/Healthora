"""create rbac and pharmacy tables

Revision ID: 20260223_0001
Revises:
Create Date: 2026-02-23 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260223_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_tables = set(inspector.get_table_names())

    if "roles" not in existing_tables:
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("display_name", sa.String(length=120), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)
    else:
        role_columns = {col["name"] for col in inspector.get_columns("roles")}
        if "display_name" not in role_columns:
            op.add_column("roles", sa.Column("display_name", sa.String(length=120), nullable=True))
            op.execute("UPDATE roles SET display_name = name WHERE display_name IS NULL")
            op.alter_column("roles", "display_name", existing_type=sa.String(length=120), nullable=False)

    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=100), nullable=False),
            sa.Column("password", sa.String(length=255), nullable=False),
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
            sa.PrimaryKeyConstraint("user_id"),
            sa.UniqueConstraint("username"),
        )
        op.create_index(op.f("ix_users_user_id"), "users", ["user_id"], unique=False)
        op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)

    if "patients" not in existing_tables:
        op.create_table(
            "patients",
            sa.Column("patient_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("gender", sa.String(length=20), nullable=True),
            sa.Column("contact", sa.String(length=40), nullable=True),
            sa.Column("dob", sa.Date(), nullable=True),
            sa.PrimaryKeyConstraint("patient_id"),
        )
        op.create_index(op.f("ix_patients_patient_id"), "patients", ["patient_id"], unique=False)

    if "drugs" not in existing_tables:
        op.create_table(
            "drugs",
            sa.Column("drug_id", sa.Integer(), nullable=False),
            sa.Column("drug_name", sa.String(length=150), nullable=False),
            sa.Column("generic_name", sa.String(length=150), nullable=True),
            sa.Column("formulation", sa.String(length=80), nullable=True),
            sa.Column("strength", sa.String(length=50), nullable=True),
            sa.Column("schedule_type", sa.String(length=50), nullable=True),
            sa.PrimaryKeyConstraint("drug_id"),
        )
        op.create_index(op.f("ix_drugs_drug_id"), "drugs", ["drug_id"], unique=False)
        op.create_index(op.f("ix_drugs_drug_name"), "drugs", ["drug_name"], unique=False)

    if "drug_batches" not in existing_tables:
        op.create_table(
            "drug_batches",
            sa.Column("batch_id", sa.Integer(), nullable=False),
            sa.Column("drug_id", sa.Integer(), nullable=False),
            sa.Column("batch_no", sa.String(length=80), nullable=False),
            sa.Column("expiry_date", sa.Date(), nullable=False),
            sa.Column("purchase_price", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("selling_price", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("quantity_available", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["drug_id"], ["drugs.drug_id"]),
            sa.PrimaryKeyConstraint("batch_id"),
            sa.UniqueConstraint("batch_no"),
        )
        op.create_index(op.f("ix_drug_batches_batch_id"), "drug_batches", ["batch_id"], unique=False)
        op.create_index(op.f("ix_drug_batches_drug_id"), "drug_batches", ["drug_id"], unique=False)
        op.create_index(op.f("ix_drug_batches_expiry_date"), "drug_batches", ["expiry_date"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "drug_batches" in tables:
        op.drop_table("drug_batches")
    if "drugs" in tables:
        op.drop_table("drugs")
    if "patients" in tables:
        op.drop_table("patients")
    if "users" in tables:
        op.drop_table("users")
    if "roles" in tables:
        op.drop_table("roles")
