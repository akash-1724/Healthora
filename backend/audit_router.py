from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps import require_permission
from models import AuditLog, User
from schemas import AuditLogRead

router = APIRouter(prefix="/api", tags=["audit"])


def to_audit_read(log: AuditLog) -> AuditLogRead:
    return AuditLogRead(
        log_id=log.log_id,
        actor_username=log.actor.username if log.actor else None,
        action=log.action,
        target_table=log.target_table,
        target_id=log.target_id,
        detail=log.detail,
        ip_address=log.ip_address,
        timestamp=log.timestamp,
    )


@router.get("/audit-logs", response_model=list[AuditLogRead], dependencies=[Depends(require_permission("view_audit_logs"))])
def list_audit_logs(skip: int = 0, limit: int = 100, action: str | None = None, db: Session = Depends(get_db)):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    logs = q.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return [to_audit_read(log) for log in logs]
