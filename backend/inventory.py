from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from auth import require_role
from database import get_db
from models import InventoryItem

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("")
def get_inventory(current_user: object = Depends(require_role("System Admin", "Chief Medical Officer", "Pharmacy Manager", "Senior Pharmacist", "Staff Pharmacist", "Inventory Clerk")), db: Session = Depends(get_db)):
    items = db.query(InventoryItem).all()
    is_admin = getattr(current_user.role, "name", None) == "System Admin"
    result = []
    for item in items:
        base = {
            "id": item.id,
            "name": item.name,
            "batch": item.batch,
            "expiry": item.expiry,
            "quantity": item.quantity,
        }
        if is_admin:
            base["price"] = round(item.price, 2)
        result.append(base)
    return result
