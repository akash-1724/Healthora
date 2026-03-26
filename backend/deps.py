from collections.abc import Callable

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User
from security import decode_token


ROLE_PERMISSIONS = {
    "system_admin": {
        "manage_users",
        "view_dashboard_summary",
        "view_patients",
        "view_drugs",
        "view_inventory",
        "view_prescriptions",
        "view_dispensing",
        "dispense_drugs",
        "manage_inventory",
        "view_audit_logs",
        "view_suppliers",
        "manage_suppliers",
        "view_ai_report",
    },
    "chief_medical_officer": {
        "view_dashboard_summary",
        "view_patients",
        "view_drugs",
        "view_prescriptions",
        "view_dispensing",
        "view_ai_report",
    },
    "pharmacy_manager": {
        "view_dashboard_summary",
        "view_drugs",
        "add_drug",
        "add_batch",
        "view_inventory",
        "update_inventory",
        "manage_inventory",
        "view_prescriptions",
        "view_dispensing",
        "dispense_drugs",
        "view_suppliers",
        "manage_suppliers",
        "view_ai_report",
    },
    "senior_pharmacist": {
        "view_dashboard_summary",
        "view_drugs",
        "add_batch",
        "view_inventory",
        "update_inventory",
        "view_prescriptions",
        "add_prescriptions",
        "view_dispensing",
        "dispense_drugs",
    },
    "staff_pharmacist": {
        "view_dashboard_summary",
        "view_drugs",
        "view_inventory",
        "update_inventory",
        "view_prescriptions",
        "view_dispensing",
        "dispense_drugs",
    },
    "inventory_clerk": {
        "view_dashboard_summary",
        "view_drugs",
        "view_inventory",
        "update_inventory",
        "view_suppliers",
        "view_patients",
        "add_patients",
    },
    "doctor": {
        "view_dashboard_summary",
        "view_patients",
        "view_drugs",
        "view_prescriptions",
        "add_prescriptions",
    },
}


ROLE_MODULES = {
    "system_admin": ["dashboard", "users", "patients", "inventory", "prescriptions", "dispensing", "suppliers", "purchase_orders", "reorder_recommendation", "audit", "ai_report"],
    "chief_medical_officer": ["dashboard", "patients", "inventory", "prescriptions", "dispensing", "ai_report"],
    "pharmacy_manager": ["dashboard", "inventory", "prescriptions", "dispensing", "suppliers", "purchase_orders", "reorder_recommendation", "ai_report"],
    "senior_pharmacist": ["dashboard", "inventory", "prescriptions", "dispensing"],
    "staff_pharmacist": ["dashboard", "inventory", "dispensing"],
    "inventory_clerk": ["dashboard", "patients", "inventory", "suppliers"],
    "doctor": ["dashboard", "patients", "inventory", "prescriptions"],
}


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token_value = authorization.split(" ", 1)[1]
    payload = decode_token(token_value)
    username = payload.get("sub")

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_permission(permission: str) -> Callable:
    def checker(current_user: User = Depends(get_current_user)) -> User:
        role_name = current_user.role.name if current_user.role else ""
        allowed = ROLE_PERMISSIONS.get(role_name, set())
        if permission not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return current_user

    return checker
