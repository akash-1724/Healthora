from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import Notification, User
from schemas import NotificationRead

router = APIRouter(prefix="/api", tags=["notifications"])


def to_notification_read(n: Notification) -> NotificationRead:
    return NotificationRead(
        notification_id=n.notification_id,
        title=n.title,
        message=n.message,
        is_read=n.is_read,
        created_at=n.created_at,
    )


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = (
        db.query(Notification)
        .filter(Notification.recipient_user_id == current_user.user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return [to_notification_read(n) for n in items]


@router.patch("/notifications/{notification_id}/read")
def mark_read(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = (
        db.query(Notification)
        .filter(Notification.notification_id == notification_id, Notification.recipient_user_id == current_user.user_id)
        .first()
    )
    if notif:
        notif.is_read = True
        db.commit()
    return {"message": "ok"}


@router.patch("/notifications/read-all")
def mark_all_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.recipient_user_id == current_user.user_id,
        Notification.is_read.is_(False),
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}


@router.delete("/notifications/clear")
def clear_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.recipient_user_id == current_user.user_id).delete()
    db.commit()
    return {"message": "Notifications cleared"}
