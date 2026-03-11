from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(120), nullable=False)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=True)
    email = Column(String(150), nullable=True)
    phone = Column(String(40), nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    department = Column(String(120), nullable=False, default="Pharmacy")
    is_active = Column(Boolean, default=True, nullable=False)
    failed_login_count = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    must_reset_password = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    role = relationship("Role", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="actor", foreign_keys="AuditLog.actor_user_id")
    notifications = relationship("Notification", back_populates="recipient")


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    address = Column(String(200), nullable=True)
    gender = Column(String(20), nullable=True)
    contact = Column(String(40), nullable=True)
    dob = Column(Date, nullable=True)
    blood_group = Column(String(10), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)

    prescriptions = relationship("Prescription", back_populates="patient")


class Drug(Base):
    __tablename__ = "drugs"

    drug_id = Column(Integer, primary_key=True, index=True)
    drug_name = Column(String(150), nullable=False, index=True)
    generic_name = Column(String(150), nullable=True)
    formulation = Column(String(80), nullable=True)
    strength = Column(String(50), nullable=True)
    schedule_type = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    low_stock_threshold = Column(Integer, default=50, nullable=False)

    batches = relationship("DrugBatch", back_populates="drug")


class DrugBatch(Base):
    __tablename__ = "drug_batches"

    batch_id = Column(Integer, primary_key=True, index=True)
    drug_id = Column(Integer, ForeignKey("drugs.drug_id"), nullable=False, index=True)
    batch_no = Column(String(80), nullable=False, unique=True)
    expiry_date = Column(Date, nullable=False, index=True)
    purchase_price = Column(Numeric(10, 2), nullable=False)
    selling_price = Column(Numeric(10, 2), nullable=False)
    quantity_available = Column(Integer, nullable=False, default=0)
    is_expired = Column(Boolean, default=False, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.supplier_id"), nullable=True)

    drug = relationship("Drug", back_populates="batches")
    supplier = relationship("Supplier", back_populates="batches")
    dispensing_records = relationship("DispensingRecord", back_populates="batch")


# ─── Supplier & Purchase ─────────────────────────────────────────────────────

class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    contact_person = Column(String(150), nullable=True)
    phone = Column(String(40), nullable=True)
    email = Column(String(150), nullable=True)
    address = Column(String(300), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    batches = relationship("DrugBatch", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    po_id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.supplier_id"), nullable=False)
    ordered_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    status = Column(String(50), nullable=False, default="pending")  # pending, received, cancelled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    received_at = Column(DateTime, nullable=True)

    supplier = relationship("Supplier", back_populates="purchase_orders")
    ordered_by = relationship("User", foreign_keys=[ordered_by_user_id])
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    item_id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.po_id"), nullable=False)
    drug_id = Column(Integer, ForeignKey("drugs.drug_id"), nullable=False)
    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, nullable=False, default=0)
    unit_price = Column(Numeric(10, 2), nullable=True)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    drug = relationship("Drug")


# ─── Prescription & Dispensing ───────────────────────────────────────────────

class Prescription(Base):
    __tablename__ = "prescriptions"

    prescription_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    doctor_name = Column(String(150), nullable=False)
    diagnosis = Column(String(300), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="open")  # open, dispensed, cancelled
    created_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="prescriptions")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")
    dispensing_records = relationship("DispensingRecord", back_populates="prescription")


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    item_id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.prescription_id"), nullable=False)
    drug_id = Column(Integer, ForeignKey("drugs.drug_id"), nullable=False)
    dosage = Column(String(100), nullable=True)
    duration = Column(String(100), nullable=True)
    quantity_prescribed = Column(Integer, nullable=False, default=1)

    prescription = relationship("Prescription", back_populates="items")
    drug = relationship("Drug")


class DispensingRecord(Base):
    __tablename__ = "dispensing_records"

    record_id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.prescription_id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("drug_batches.batch_id"), nullable=False)
    quantity_dispensed = Column(Integer, nullable=False)
    dispensed_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    dispensed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)

    prescription = relationship("Prescription", back_populates="dispensing_records")
    patient = relationship("Patient")
    batch = relationship("DrugBatch", back_populates="dispensing_records")
    dispensed_by = relationship("User", foreign_keys=[dispensed_by_user_id])


# ─── Audit Log & Notifications ───────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    action = Column(String(100), nullable=False)        # e.g. "create_user", "dispense_drug"
    target_table = Column(String(100), nullable=True)   # e.g. "users", "drug_batches"
    target_id = Column(String(50), nullable=True)       # stringified primary key
    detail = Column(Text, nullable=True)                # JSON string with old/new values
    ip_address = Column(String(60), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    actor = relationship("User", back_populates="audit_logs", foreign_keys=[actor_user_id])


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    recipient = relationship("User", back_populates="notifications")
