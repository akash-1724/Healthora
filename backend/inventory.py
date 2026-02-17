from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

inventory_data = [
    {"id": 1, "name": "Paracetamol", "stock": 120},
    {"id": 2, "name": "Syringe", "stock": 80},
    {"id": 3, "name": "Bandage", "stock": 200},
]


@router.get("")
def get_inventory(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    get_current_user(authorization, db)
    return inventory_data
