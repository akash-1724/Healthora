from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String
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
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    department = Column(String(120), nullable=False, default="Pharmacy")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    role = relationship("Role", back_populates="users")


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    address = Column(String(200), nullable=True)
    gender = Column(String(20), nullable=True)
    contact = Column(String(40), nullable=True)
    dob = Column(Date, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)


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

    drug = relationship("Drug", back_populates="batches")
