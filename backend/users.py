from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user, require_permission
from models import Role, User
from schemas import PasswordResetRequest, RoleRead, UserCreate, UserRead, UserUpdate
from security import hash_password

router = APIRouter(prefix="/api", tags=["users"])


DEPARTMENTS = [
    "Cardiology",
    "Neurology",
    "Main Pharmacy",
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


DEPARTMENT_ROLE_MAP = {
    "Administration": {"inventory_clerk", "system_admin", "chief_medical_officer"},
}


def _allowed_role_names_for_department(department: str) -> set[str]:
    if department == "Pharmacy":
        department = "Main Pharmacy"
    if department in DEPARTMENT_ROLE_MAP:
        return DEPARTMENT_ROLE_MAP[department]
    return {"pharmacy_manager", "staff_pharmacist", "doctor"}


def _validate_department_role(department: str, role_name: str):
    allowed = _allowed_role_names_for_department(department)
    if role_name not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Role '{role_name}' is not allowed for department '{department}'",
        )


def to_user_read(user: User) -> UserRead:
    return UserRead(
        user_id=user.user_id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        role_id=user.role_id,
        role_name=user.role.name,
        role_display_name=user.role.display_name,
        department=user.department,
        is_active=user.is_active,
        failed_login_count=user.failed_login_count,
        locked_until=user.locked_until,
        last_login_at=user.last_login_at,
        password_changed_at=user.password_changed_at,
        must_reset_password=user.must_reset_password,
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


@router.post("/users", response_model=UserRead, dependencies=[Depends(require_permission("manage_users")), Depends(require_permission("add_users"))])
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    if not payload.password or len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role_id")

    _validate_department_role(payload.department, role.name)

    new_user = User(
        username=payload.username,
        password=hash_password(payload.password),
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        role_id=payload.role_id,
        department=payload.department,
        is_active=payload.is_active,
        failed_login_count=0,
        must_reset_password=False,
        password_changed_at=datetime.utcnow(),
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

    next_role = user.role
    next_department = user.department

    if payload.role_id is not None:
        role = db.query(Role).filter(Role.id == payload.role_id).first()
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role_id")
        next_role = role
    if payload.department is not None:
        next_department = payload.department

    _validate_department_role(next_department, next_role.name)

    user.role_id = next_role.id
    user.department = next_department
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.email is not None:
        user.email = payload.email
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.must_reset_password is not None:
        user.must_reset_password = payload.must_reset_password

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
    if not payload.password or len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user.password = hash_password(payload.password)
    user.password_changed_at = datetime.utcnow()
    user.must_reset_password = False
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
