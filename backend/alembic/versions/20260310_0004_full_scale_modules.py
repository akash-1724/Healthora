"""Add new modules: suppliers, purchase_orders, prescriptions, dispensing, audit_logs, notifications; add blood_group to patients, supplier_id to drug_batches

Revision ID: 20260310_0004
Revises: 20260223_0003
Create Date: 2026-03-10 22:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260310_0004"
down_revision: Union[str, Sequence[str], None] = "20260223_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = inspector.get_table_names()

    # ── patients: add blood_group ───────────────────────────────────────────
    patient_cols = {col["name"] for col in inspector.get_columns("patients")} if "patients" in existing_tables else set()
    if "blood_group" not in patient_cols:
        op.add_column("patients", sa.Column("blood_group", sa.String(10), nullable=True))

    # ── suppliers ──────────────────────────────────────────────────────────
    if "suppliers" not in existing_tables:
        op.create_table(
            "suppliers",
            sa.Column("supplier_id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("contact_person", sa.String(150), nullable=True),
            sa.Column("phone", sa.String(40), nullable=True),
            sa.Column("email", sa.String(150), nullable=True),
            sa.Column("address", sa.String(300), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # ── drug_batches: add supplier_id FK ──────────────────────────────────
    batch_cols = {col["name"] for col in inspector.get_columns("drug_batches")} if "drug_batches" in existing_tables else set()
    if "supplier_id" not in batch_cols:
        op.add_column("drug_batches", sa.Column("supplier_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_drug_batches_supplier", "drug_batches", "suppliers", ["supplier_id"], ["supplier_id"])

    # ── purchase_orders ────────────────────────────────────────────────────
    if "purchase_orders" not in existing_tables:
        op.create_table(
            "purchase_orders",
            sa.Column("po_id", sa.Integer(), primary_key=True),
            sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.supplier_id"), nullable=False),
            sa.Column("ordered_by_user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=True),
            sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("received_at", sa.DateTime(), nullable=True),
        )

    if "purchase_order_items" not in existing_tables:
        op.create_table(
            "purchase_order_items",
            sa.Column("item_id", sa.Integer(), primary_key=True),
            sa.Column("po_id", sa.Integer(), sa.ForeignKey("purchase_orders.po_id"), nullable=False),
            sa.Column("drug_id", sa.Integer(), sa.ForeignKey("drugs.drug_id"), nullable=False),
            sa.Column("quantity_ordered", sa.Integer(), nullable=False),
            sa.Column("quantity_received", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("unit_price", sa.Numeric(10, 2), nullable=True),
        )

    # ── prescriptions ──────────────────────────────────────────────────────
    if "prescriptions" not in existing_tables:
        op.create_table(
            "prescriptions",
            sa.Column("prescription_id", sa.Integer(), primary_key=True),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.patient_id"), nullable=False),
            sa.Column("doctor_name", sa.String(150), nullable=False),
            sa.Column("diagnosis", sa.String(300), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(50), nullable=False, server_default="open"),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if "prescription_items" not in existing_tables:
        op.create_table(
            "prescription_items",
            sa.Column("item_id", sa.Integer(), primary_key=True),
            sa.Column("prescription_id", sa.Integer(), sa.ForeignKey("prescriptions.prescription_id"), nullable=False),
            sa.Column("drug_id", sa.Integer(), sa.ForeignKey("drugs.drug_id"), nullable=False),
            sa.Column("dosage", sa.String(100), nullable=True),
            sa.Column("duration", sa.String(100), nullable=True),
            sa.Column("quantity_prescribed", sa.Integer(), nullable=False, server_default="1"),
        )

    # ── dispensing_records ─────────────────────────────────────────────────
    if "dispensing_records" not in existing_tables:
        op.create_table(
            "dispensing_records",
            sa.Column("record_id", sa.Integer(), primary_key=True),
            sa.Column("prescription_id", sa.Integer(), sa.ForeignKey("prescriptions.prescription_id"), nullable=True),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.patient_id"), nullable=False),
            sa.Column("batch_id", sa.Integer(), sa.ForeignKey("drug_batches.batch_id"), nullable=False),
            sa.Column("quantity_dispensed", sa.Integer(), nullable=False),
            sa.Column("dispensed_by_user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("dispensed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("notes", sa.Text(), nullable=True),
        )

    # ── audit_logs ────────────────────────────────────────────────────────
    if "audit_logs" not in existing_tables:
        op.create_table(
            "audit_logs",
            sa.Column("log_id", sa.Integer(), primary_key=True),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=True),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("target_table", sa.String(100), nullable=True),
            sa.Column("target_id", sa.String(50), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(60), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # ── notifications ─────────────────────────────────────────────────────
    if "notifications" not in existing_tables:
        op.create_table(
            "notifications",
            sa.Column("notification_id", sa.Integer(), primary_key=True),
            sa.Column("recipient_user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = inspector.get_table_names()

    for tbl in ["notifications", "audit_logs", "dispensing_records", "prescription_items",
                 "prescriptions", "purchase_order_items", "purchase_orders"]:
        if tbl in existing_tables:
            op.drop_table(tbl)

    if "drug_batches" in existing_tables:
        batch_cols = {col["name"] for col in inspector.get_columns("drug_batches")}
        if "supplier_id" in batch_cols:
            op.drop_constraint("fk_drug_batches_supplier", "drug_batches", type_="foreignkey")
            op.drop_column("drug_batches", "supplier_id")

    if "suppliers" in existing_tables:
        op.drop_table("suppliers")

    if "patients" in existing_tables:
        patient_cols = {col["name"] for col in inspector.get_columns("patients")}
        if "blood_group" in patient_cols:
            op.drop_column("patients", "blood_group")
