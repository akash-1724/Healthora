from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
def list_users(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    get_current_user(authorization, db)
    users = db.query(User).all()
    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "role_id": user.role_id,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
        for user in users
    ]


@router.post("")
def create_user(payload: dict, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    get_current_user(authorization, db)
    new_user = User(
        username=payload.get("username"),
        password=payload.get("password"),
        role_id=payload.get("role_id", 1),
        is_active=payload.get("is_active", True),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "user_id": new_user.user_id,
        "username": new_user.username,
        "role_id": new_user.role_id,
        "is_active": new_user.is_active,
        "created_at": new_user.created_at,
    }
