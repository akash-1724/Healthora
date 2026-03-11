"""
Audit logging utility — call log_action from any route to persist an audit record.
"""
import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import AuditLog


def log_action(
    db: Session,
    action: str,
    actor_user_id: Optional[int] = None,
    target_table: Optional[str] = None,
    target_id: Optional[Any] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_table=target_table,
        target_id=str(target_id) if target_id is not None else None,
        detail=json.dumps(detail) if detail else None,
        ip_address=ip_address,
        timestamp=datetime.utcnow(),
    )
    db.add(entry)
    # Flush but let the calling route commit so it's part of the same transaction
    db.flush()
