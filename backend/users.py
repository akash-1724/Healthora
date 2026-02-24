from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user, require_permission
from models import Role, User
from schemas import PasswordResetRequest, RoleRead, UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/api", tags=["users"])


DEPARTMENTS = [
    "Cardiology",
    "Neurology",
    "Pharmacy",
    "Emergency",
    "Pediatrics",
    "Oncology",
    "General Medicine",
    "Radiology",
    "Orthopedics",
    "ICU",
    "Outpatient (OPD)",
    "Laboratory",
    "Administration",
]


def to_user_read(user: User) -> UserRead:
    return UserRead(
        user_id=user.user_id,
        username=user.username,
        role_id=user.role_id,
        role_name=user.role.name,
        role_display_name=user.role.display_name,
        department=user.department,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("/roles", response_model=list[RoleRead], dependencies=[Depends(require_permission("manage_users"))])
def list_roles(db: Session = Depends(get_db)):
    return db.query(Role).order_by(Role.id.asc()).all()


@router.get("/departments", response_model=list[str], dependencies=[Depends(require_permission("manage_users"))])
def list_departments():
    return DEPARTMENTS


@router.get("/users", response_model=list[UserRead], dependencies=[Depends(require_permission("manage_users"))])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.user_id.asc()).all()
    return [to_user_read(user) for user in users]


@router.post("/users", response_model=UserRead, dependencies=[Depends(require_permission("manage_users"))])
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role_id")

    max_user = db.query(User.user_id).order_by(User.user_id.desc()).first()
    next_user_id = (max_user[0] if max_user else 0) + 1

    new_user = User(
        user_id=next_user_id,
        username=payload.username,
        password=payload.password,
        role_id=payload.role_id,
        department=payload.department,
        is_active=payload.is_active,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return to_user_read(new_user)


@router.put("/users/{user_id}", response_model=UserRead, dependencies=[Depends(require_permission("manage_users"))])
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role_id is not None:
        role = db.query(Role).filter(Role.id == payload.role_id).first()
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role_id")
        user.role_id = payload.role_id
    if payload.department is not None:
        user.department = payload.department
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return to_user_read(user)


@router.patch("/users/{user_id}/deactivate", response_model=UserRead, dependencies=[Depends(require_permission("manage_users"))])
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return to_user_read(user)


@router.patch("/users/{user_id}/reset-password", response_model=UserRead, dependencies=[Depends(require_permission("manage_users"))])
def reset_password(user_id: int, payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password = payload.password
    db.commit()
    db.refresh(user)
    return to_user_read(user)


@router.delete("/users/{user_id}", dependencies=[Depends(require_permission("manage_users"))])
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}
