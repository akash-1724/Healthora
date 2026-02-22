from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session, joinedload

from auth import require_role, hash_password
from database import get_db
from models import User, Role

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("")
def list_users(current_user: User = Depends(require_role("System Admin")), db: Session = Depends(get_db)):
    users = db.query(User).options(joinedload(User.role)).all()
    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "role_id": user.role_id,
            "role": user.role.name if user.role else None,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
        for user in users
    ]


@router.get("/roles")
def list_roles(db: Session = Depends(get_db)):
    # Roles are not sensitive; allow the frontend to fetch available roles
    # without requiring admin privileges so the add-user UI can populate.
    roles = db.query(Role).all()
    return [{"id": r.id, "name": r.name} for r in roles]
@router.post("")
def create_user(payload: dict, current_user: User = Depends(require_role("System Admin")), db: Session = Depends(get_db)):
    new_user = User(
        username=payload.get("username"),
        password=hash_password(payload.get("password") or ""),
        role_id=payload.get("role_id"),
        is_active=payload.get("is_active", True),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    # Reload with role relationship
    db.expunge(new_user)
    new_user = db.query(User).options(joinedload(User.role)).filter(User.user_id == new_user.user_id).first()
    return {
        "user_id": new_user.user_id,
        "username": new_user.username,
        "role_id": new_user.role_id,
        "role": new_user.role.name if new_user.role else None,
        "is_active": new_user.is_active,
        "created_at": new_user.created_at,
    }


@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, payload: dict, current_user: User = Depends(require_role("System Admin")), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return {"error": "user not found"}
    new_password = payload.get("password")
    if not new_password:
        return {"error": "password required"}
    user.password = hash_password(new_password)
    db.add(user)
    db.commit()
    return {"ok": True}

@router.put("/{user_id}")
def update_user(user_id: int, payload: dict, current_user: User = Depends(require_role("System Admin")), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return {"error": "user not found"}
    
    if "role_id" in payload:
        user.role_id = payload.get("role_id")
    if "is_active" in payload:
        user.is_active = payload.get("is_active")
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Reload with role relationship
    db.expunge(user)
    user = db.query(User).options(joinedload(User.role)).filter(User.user_id == user_id).first()
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role_id": user.role_id,
        "role": user.role.name if user.role else None,
        "is_active": user.is_active,
        "created_at": user.created_at,
    }