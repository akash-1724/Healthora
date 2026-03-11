from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from audit import log_action
from database import get_db
from deps import get_current_user, require_permission
from models import Drug, PurchaseOrder, PurchaseOrderItem, Supplier, User
from schemas import (
    PurchaseOrderCreate,
    PurchaseOrderItemRead,
    PurchaseOrderRead,
    PurchaseOrderStatusUpdate,
)

router = APIRouter(prefix="/api", tags=["purchase_orders"])


def to_po_read(po: PurchaseOrder) -> PurchaseOrderRead:
    return PurchaseOrderRead(
        po_id=po.po_id,
        supplier_id=po.supplier_id,
        supplier_name=po.supplier.name if po.supplier else "",
        ordered_by_username=po.ordered_by.username if po.ordered_by else None,
        status=po.status,
        notes=po.notes,
        created_at=po.created_at,
        received_at=po.received_at,
        items=[
            PurchaseOrderItemRead(
                item_id=item.item_id,
                drug_id=item.drug_id,
                drug_name=item.drug.drug_name if item.drug else "",
                quantity_ordered=item.quantity_ordered,
                quantity_received=item.quantity_received,
                unit_price=float(item.unit_price) if item.unit_price else None,
            )
            for item in po.items
        ],
    )


@router.get("/purchase-orders", response_model=list[PurchaseOrderRead], dependencies=[Depends(require_permission("manage_inventory"))])
def list_purchase_orders(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    orders = db.query(PurchaseOrder).order_by(PurchaseOrder.po_id.desc()).offset(skip).limit(limit).all()
    return [to_po_read(po) for po in orders]


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderRead, dependencies=[Depends(require_permission("manage_inventory"))])
def get_purchase_order(po_id: int, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.po_id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return to_po_read(po)


@router.post("/purchase-orders", response_model=PurchaseOrderRead, dependencies=[Depends(require_permission("manage_inventory"))])
def create_purchase_order(payload: PurchaseOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    supplier = db.query(Supplier).filter(Supplier.supplier_id == payload.supplier_id, Supplier.is_active.is_(True)).first()
    if not supplier:
        raise HTTPException(status_code=400, detail="Supplier not found or inactive")

    po = PurchaseOrder(
        supplier_id=payload.supplier_id,
        ordered_by_user_id=current_user.user_id,
        notes=payload.notes,
        status="pending",
    )
    db.add(po)
    db.flush()

    for item in payload.items:
        drug = db.query(Drug).filter(Drug.drug_id == item.drug_id).first()
        if not drug:
            raise HTTPException(status_code=400, detail=f"Drug id {item.drug_id} not found")
        db.add(PurchaseOrderItem(
            po_id=po.po_id,
            drug_id=item.drug_id,
            quantity_ordered=item.quantity_ordered,
            unit_price=item.unit_price,
        ))

    log_action(db, "create_purchase_order", actor_user_id=current_user.user_id, target_table="purchase_orders", target_id=po.po_id)
    db.commit()
    db.refresh(po)
    return to_po_read(po)


@router.patch("/purchase-orders/{po_id}/status", response_model=PurchaseOrderRead, dependencies=[Depends(require_permission("manage_inventory"))])
def update_po_status(po_id: int, payload: PurchaseOrderStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.po_id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if payload.status not in ("received", "cancelled"):
        raise HTTPException(status_code=400, detail="Status must be 'received' or 'cancelled'")
    po.status = payload.status
    if payload.status == "received":
        po.received_at = datetime.utcnow()
    log_action(db, f"po_status_{payload.status}", actor_user_id=current_user.user_id, target_table="purchase_orders", target_id=po_id)
    db.commit()
    db.refresh(po)
    return to_po_read(po)
