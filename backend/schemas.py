from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token: str
    token_type: str
    role: str
    display_name: str
    must_reset_password: bool = False


class SetupStatusResponse(BaseModel):
    requires_sysadmin_setup: bool


class RegisterSysAdminRequest(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bootstrap_key: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class CreateSysAdminRequest(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


# ─── Roles & Users ───────────────────────────────────────────────────────────

class RoleRead(BaseModel):
    id: int
    name: str
    display_name: str

    class Config:
        from_attributes = True


class UserRead(BaseModel):
    user_id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role_id: int
    role_name: str
    role_display_name: str
    department: str
    is_active: bool
    failed_login_count: int
    locked_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    must_reset_password: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role_id: int
    department: str = "Pharmacy"
    is_active: bool = True

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role_id: Optional[int] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None
    must_reset_password: Optional[bool] = None


class PasswordResetRequest(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserProfile(BaseModel):
    user_id: int
    username: str
    role: str
    display_name: str
    is_active: bool


class DashboardAccess(BaseModel):
    role: str
    display_name: str
    modules: list[str]
    permissions: list[str]


# ─── Patients ────────────────────────────────────────────────────────────────

class PatientRead(BaseModel):
    patient_id: int
    name: str
    address: Optional[str] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    dob: Optional[date] = None
    blood_group: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_by: Optional[str] = None
    created_at: datetime
    is_archived: bool


class PatientCreate(BaseModel):
    name: str
    address: Optional[str] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    dob: Optional[date] = None
    blood_group: Optional[str] = None


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    dob: Optional[date] = None
    blood_group: Optional[str] = None


# ─── Drugs & Batches ─────────────────────────────────────────────────────────

class DrugRead(BaseModel):
    drug_id: int
    drug_name: str
    generic_name: Optional[str] = None
    formulation: Optional[str] = None
    strength: Optional[str] = None
    schedule_type: Optional[str] = None
    is_active: bool
    low_stock_threshold: int
    total_quantity: int = 0
    active_batches: int = 0


class DrugCreate(BaseModel):
    drug_name: str
    generic_name: Optional[str] = None
    formulation: Optional[str] = None
    strength: Optional[str] = None
    schedule_type: Optional[str] = None
    low_stock_threshold: int = 50


class DrugUpdate(BaseModel):
    drug_name: Optional[str] = None
    generic_name: Optional[str] = None
    formulation: Optional[str] = None
    strength: Optional[str] = None
    schedule_type: Optional[str] = None
    low_stock_threshold: Optional[int] = None
    is_active: Optional[bool] = None


class DrugBatchRead(BaseModel):
    batch_id: int
    drug_id: int
    drug_name: str
    batch_no: str
    expiry_date: date
    purchase_price: float
    selling_price: float
    quantity_available: int
    is_expired: bool
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None


class DrugBatchCreate(BaseModel):
    drug_id: int
    batch_no: str
    expiry_date: date
    purchase_price: float
    selling_price: float
    quantity_available: int
    supplier_id: Optional[int] = None

    @field_validator("purchase_price", "selling_price")
    @classmethod
    def non_negative_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v

    @field_validator("quantity_available")
    @classmethod
    def non_negative_quantity(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        return v


class InventoryUpdate(BaseModel):
    quantity_available: int

    @field_validator("quantity_available")
    @classmethod
    def non_negative_quantity(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        return v


# ─── Suppliers ───────────────────────────────────────────────────────────────

class SupplierRead(BaseModel):
    supplier_id: int
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    created_at: datetime


class SupplierCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


# ─── Purchase Orders ─────────────────────────────────────────────────────────

class PurchaseOrderItemCreate(BaseModel):
    drug_id: int
    quantity_ordered: int
    unit_price: Optional[float] = None

    @field_validator("quantity_ordered")
    @classmethod
    def positive_quantity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity_ordered must be greater than zero")
        return v


class PurchaseOrderItemRead(BaseModel):
    item_id: int
    drug_id: int
    drug_name: str
    quantity_ordered: int
    quantity_received: int
    unit_price: Optional[float] = None


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    notes: Optional[str] = None
    items: list[PurchaseOrderItemCreate]


class PurchaseOrderRead(BaseModel):
    po_id: int
    supplier_id: int
    supplier_name: str
    ordered_by_username: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    received_at: Optional[datetime] = None
    items: list[PurchaseOrderItemRead] = []


class PurchaseOrderStatusUpdate(BaseModel):
    status: str  # received | cancelled


# ─── Prescriptions ───────────────────────────────────────────────────────────

class PrescriptionItemCreate(BaseModel):
    drug_id: int
    dosage: Optional[str] = None
    duration: Optional[str] = None
    quantity_prescribed: int = 1


class PrescriptionItemRead(BaseModel):
    item_id: int
    drug_id: int
    drug_name: str
    dosage: Optional[str] = None
    duration: Optional[str] = None
    quantity_prescribed: int


class PrescriptionCreate(BaseModel):
    patient_id: int
    doctor_name: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    items: list[PrescriptionItemCreate]


class PrescriptionRead(BaseModel):
    prescription_id: int
    patient_id: int
    patient_name: str
    doctor_name: str
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    status: str
    created_by_username: Optional[str] = None
    created_at: datetime
    items: list[PrescriptionItemRead] = []


# ─── Dispensing ──────────────────────────────────────────────────────────────

class DispensingRecordCreate(BaseModel):
    prescription_id: Optional[int] = None
    patient_id: int
    batch_id: int
    quantity_dispensed: int
    notes: Optional[str] = None

    @field_validator("quantity_dispensed")
    @classmethod
    def positive_quantity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity_dispensed must be greater than zero")
        return v


class DispensingRecordRead(BaseModel):
    record_id: int
    prescription_id: Optional[int] = None
    patient_id: int
    patient_name: str
    batch_id: int
    drug_name: str
    batch_no: str
    quantity_dispensed: int
    dispensed_by_username: str
    dispensed_at: datetime
    notes: Optional[str] = None


# ─── Audit Log ───────────────────────────────────────────────────────────────

class AuditLogRead(BaseModel):
    log_id: int
    actor_username: Optional[str] = None
    action: str
    target_table: Optional[str] = None
    target_id: Optional[str] = None
    detail: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime


# ─── Notifications ───────────────────────────────────────────────────────────

class NotificationRead(BaseModel):
    notification_id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime


# ─── Dashboard ───────────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    usable_stock: int
    total_stock: int
    expiry_risk: int
    low_stock_alerts: int
    total_patients: int
    total_dispensed_today: int = 0
