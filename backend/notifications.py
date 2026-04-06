from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import Drug, DrugBatch, Notification, User
from schemas import NotificationRead

router = APIRouter(prefix="/api", tags=["notifications"])


def _ensure_notifications_for_user(current_user: User, db: Session) -> None:
    today = date.today()

    expiry_batch = (
        db.query(DrugBatch)
        .join(Drug, Drug.drug_id == DrugBatch.drug_id)
        .filter(
            DrugBatch.is_expired.is_(False),
            DrugBatch.quantity_available > 0,
            DrugBatch.expiry_date >= today,
        )
        .order_by(DrugBatch.expiry_date.asc())
        .first()
    )

    if expiry_batch and (expiry_batch.expiry_date - today).days <= 90:
        title = f"Expiry Alert: {expiry_batch.drug.drug_name} nearing expiry"
        exists = (
            db.query(Notification)
            .filter(
                Notification.recipient_user_id == current_user.user_id,
                Notification.title == title,
            )
            .first()
        )
        if not exists:
            db.add(
                Notification(
                    recipient_user_id=current_user.user_id,
                    title=title,
                    message=(
                        f"Batch {expiry_batch.batch_no} expires on {expiry_batch.expiry_date}. "
                        "Please plan dispensing and reorder if needed."
                    ),
                    is_read=False,
                )
            )

    low_stock = (
        db.query(
            Drug.drug_name,
            func.coalesce(func.sum(DrugBatch.quantity_available), 0).label("stock"),
        )
        .outerjoin(DrugBatch, DrugBatch.drug_id == Drug.drug_id)
        .group_by(Drug.drug_id, Drug.drug_name)
        .having(
            func.coalesce(func.sum(DrugBatch.quantity_available), 0)
            < Drug.low_stock_threshold
        )
        .order_by(func.coalesce(func.sum(DrugBatch.quantity_available), 0).asc())
        .first()
    )
    if low_stock:
        title = "Reorder Suggestion: Low stock medicine"
        exists = (
            db.query(Notification)
            .filter(
                Notification.recipient_user_id == current_user.user_id,
                Notification.title == title,
            )
            .first()
        )
        if not exists:
            db.add(
                Notification(
                    recipient_user_id=current_user.user_id,
                    title=title,
                    message=(
                        f"{low_stock.drug_name} is low in stock (current total: {int(low_stock.stock)}). "
                        "Please review purchase orders."
                    ),
                    is_read=False,
                )
            )

    db.commit()


def to_notification_read(n: Notification) -> NotificationRead:
    return NotificationRead(
        notification_id=n.notification_id,
        title=n.title,
        message=n.message,
        is_read=n.is_read,
        created_at=n.created_at,
    )


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _ensure_notifications_for_user(current_user, db)
    items = (
        db.query(Notification)
        .filter(Notification.recipient_user_id == current_user.user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return [to_notification_read(n) for n in items]


@router.patch("/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(
            Notification.notification_id == notification_id,
            Notification.recipient_user_id == current_user.user_id,
        )
        .first()
    )
    if notif:
        notif.is_read = True
        db.commit()
    return {"message": "ok"}


@router.patch("/notifications/read-all")
def mark_all_read(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    db.query(Notification).filter(
        Notification.recipient_user_id == current_user.user_id,
        Notification.is_read.is_(False),
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}


@router.delete("/notifications/clear")
def clear_notifications(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    db.query(Notification).filter(
        Notification.recipient_user_id == current_user.user_id
    ).delete()
    db.commit()
    return {"message": "Notifications cleared"}
