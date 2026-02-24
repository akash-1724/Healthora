from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps import ROLE_MODULES, ROLE_PERMISSIONS, get_current_user, require_permission
from models import DrugBatch, User
from schemas import DashboardAccess

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard-expiry", dependencies=[Depends(require_permission("view_dashboard_summary"))])
def dashboard_expiry_list(db: Session = Depends(get_db)):
    today = date.today()
    batches = db.query(DrugBatch).all()
    risk_rows = []
    for batch in batches:
        if batch.is_expired:
            continue
        days_left = (batch.expiry_date - today).days
        if days_left <= 90:
            risk_rows.append(
                {
                    "batch_id": batch.batch_id,
                    "drug_name": batch.drug.drug_name,
                    "batch_no": batch.batch_no,
                    "expiry_date": batch.expiry_date,
                    "days_left": days_left,
                    "quantity_available": batch.quantity_available,
                }
            )
    risk_rows.sort(key=lambda row: row["days_left"])
    return risk_rows[:10]


@router.get("/dashboard-notifications")
def dashboard_notifications(current_user: User = Depends(get_current_user)):
    role_name = current_user.role.name
    common = [
        "Expiry Alert: Some batches expire within 90 days",
        "Reorder Suggestion: Check low stock medicines",
        "Info: Weekly summary available in reports",
    ]
    role_specific = {
        "system_admin": ["System Admin: Review user access changes"],
        "chief_medical_officer": ["CMO: Review patient and prescription volume"],
        "pharmacy_manager": ["Manager: Approve pending purchase requests"],
        "senior_pharmacist": ["Senior Pharmacist: Review controlled drug movement"],
        "staff_pharmacist": ["Staff Pharmacist: Verify pending dispenses"],
        "inventory_clerk": ["Inventory Clerk: Update inward stock entries"],
    }
    return common + role_specific.get(role_name, [])


@router.get("/dashboard-access", response_model=DashboardAccess)
def dashboard_access(current_user: User = Depends(get_current_user)):
    role_name = current_user.role.name
    return DashboardAccess(
        role=role_name,
        display_name=current_user.role.display_name,
        modules=ROLE_MODULES.get(role_name, ["dashboard"]),
        permissions=sorted(list(ROLE_PERMISSIONS.get(role_name, set()))),
    )
