from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from audit import log_action
from database import get_db
from deps import get_current_user, require_permission
from models import Supplier, User
from schemas import SupplierCreate, SupplierRead, SupplierUpdate

router = APIRouter(prefix="/api", tags=["suppliers"])


def to_supplier_read(s: Supplier) -> SupplierRead:
    return SupplierRead(
        supplier_id=s.supplier_id,
        name=s.name,
        contact_person=s.contact_person,
        phone=s.phone,
        email=s.email,
        address=s.address,
        is_active=s.is_active,
        created_at=s.created_at,
    )


@router.get("/suppliers", response_model=list[SupplierRead], dependencies=[Depends(require_permission("view_suppliers"))])
def list_suppliers(db: Session = Depends(get_db)):
    return [to_supplier_read(s) for s in db.query(Supplier).order_by(Supplier.supplier_id).all()]


@router.post("/suppliers", response_model=SupplierRead, dependencies=[Depends(require_permission("manage_suppliers"))])
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.flush()
    log_action(db, "create_supplier", actor_user_id=current_user.user_id, target_table="suppliers", target_id=supplier.supplier_id)
    db.commit()
    db.refresh(supplier)
    return to_supplier_read(supplier)


@router.put("/suppliers/{supplier_id}", response_model=SupplierRead, dependencies=[Depends(require_permission("manage_suppliers"))])
def update_supplier(supplier_id: int, payload: SupplierUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    supplier = db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    log_action(db, "update_supplier", actor_user_id=current_user.user_id, target_table="suppliers", target_id=supplier_id)
    db.commit()
    db.refresh(supplier)
    return to_supplier_read(supplier)


@router.delete("/suppliers/{supplier_id}", dependencies=[Depends(require_permission("manage_suppliers"))])
def delete_supplier(supplier_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    supplier = db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    # Soft-delete
    supplier.is_active = False
    log_action(db, "deactivate_supplier", actor_user_id=current_user.user_id, target_table="suppliers", target_id=supplier_id)
    db.commit()
    return {"message": "Supplier deactivated"}
