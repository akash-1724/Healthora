from datetime import date, datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token: str
    token_type: str
    role: str
    display_name: str


class RoleRead(BaseModel):
    id: int
    name: str
    display_name: str

    class Config:
        from_attributes = True


class UserRead(BaseModel):
    user_id: int
    username: str
    role_id: int
    role_name: str
    role_display_name: str
    department: str
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    password: str
    role_id: int
    department: str = "Pharmacy"
    is_active: bool = True


class UserUpdate(BaseModel):
    role_id: int | None = None
    department: str | None = None
    is_active: bool | None = None


class PasswordResetRequest(BaseModel):
    password: str


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


class PatientRead(BaseModel):
    patient_id: int
    name: str
    address: str | None = None
    gender: str | None = None
    contact: str | None = None
    dob: date | None = None
    created_by_user_id: int | None = None
    created_at: datetime
    is_archived: bool


class PatientCreate(BaseModel):
    name: str
    address: str | None = None
    gender: str | None = None
    contact: str | None = None
    dob: date | None = None


class PatientUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    gender: str | None = None
    contact: str | None = None
    dob: date | None = None


class DrugRead(BaseModel):
    drug_id: int
    drug_name: str
    generic_name: str | None = None
    formulation: str | None = None
    strength: str | None = None
    schedule_type: str | None = None
    is_active: bool
    low_stock_threshold: int


class DrugCreate(BaseModel):
    drug_name: str
    generic_name: str | None = None
    formulation: str | None = None
    strength: str | None = None
    schedule_type: str | None = None
    low_stock_threshold: int = 50


class DrugUpdate(BaseModel):
    drug_name: str | None = None
    generic_name: str | None = None
    formulation: str | None = None
    strength: str | None = None
    schedule_type: str | None = None
    low_stock_threshold: int | None = None
    is_active: bool | None = None


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


class DrugBatchCreate(BaseModel):
    drug_id: int
    batch_no: str
    expiry_date: date
    purchase_price: float
    selling_price: float
    quantity_available: int


class InventoryUpdate(BaseModel):
    quantity_available: int


class DashboardSummary(BaseModel):
    usable_stock: int
    total_stock: int
    expiry_risk: int
    low_stock_alerts: int
    total_patients: int
