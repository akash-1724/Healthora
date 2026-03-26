import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user, require_permission
from models import Role, User
from schemas import (
    CreateSysAdminRequest,
    LoginRequest,
    LoginResponse,
    RegisterSysAdminRequest,
    SetupStatusResponse,
    UserProfile,
)
from security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api", tags=["auth"])

MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOCKOUT_MINUTES = int(os.getenv("LOCKOUT_MINUTES", "15"))


@router.get("/setup-status", response_model=SetupStatusResponse)
def setup_status(db: Session = Depends(get_db)):
    has_users = db.query(User).count() > 0
    return SetupStatusResponse(requires_sysadmin_setup=not has_users)


@router.post("/register-sysadmin", response_model=LoginResponse)
def register_sysadmin(payload: RegisterSysAdminRequest, db: Session = Depends(get_db)):
    expected_bootstrap = os.getenv("SYSADMIN_BOOTSTRAP_KEY")
    if expected_bootstrap and payload.bootstrap_key != expected_bootstrap:
        raise HTTPException(status_code=403, detail="Invalid hospital key")

    role = db.query(Role).filter(Role.name == "system_admin").first()
    if not role:
        raise HTTPException(status_code=500, detail="System admin role not configured")

    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=payload.username,
        password=hash_password(payload.password),
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        role_id=role.id,
        department="Administration",
        is_active=True,
        failed_login_count=0,
        must_reset_password=False,
        password_changed_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.username, role=role.name)
    return LoginResponse(
        access_token=token,
        token=token,
        token_type="bearer",
        role=role.name,
        display_name=role.display_name,
        must_reset_password=user.must_reset_password,
    )


@router.post("/create-sysadmin", response_model=UserProfile, dependencies=[Depends(require_permission("manage_users"))])
def create_sysadmin(payload: CreateSysAdminRequest, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.name == "system_admin").first()
    if not role:
        raise HTTPException(status_code=500, detail="System admin role not configured")

    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=payload.username,
        password=hash_password(payload.password),
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        role_id=role.id,
        department="Administration",
        is_active=True,
        failed_login_count=0,
        must_reset_password=False,
        password_changed_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserProfile(
        user_id=user.user_id,
        username=user.username,
        role=role.name,
        display_name=role.display_name,
        is_active=user.is_active,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    now = datetime.utcnow()
    if user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=423, detail=f"Account locked. Try again after {user.locked_until.isoformat()} UTC")

    if not verify_password(payload.password, user.password):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_count = 0
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Upgrade legacy plain-text password to bcrypt on successful login
    if not user.password.startswith("$2b$") and not user.password.startswith("$2a$"):
        user.password = hash_password(payload.password)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()

    role_name = user.role.name
    display_name = user.role.display_name
    token = create_access_token(subject=user.username, role=role_name)
    return LoginResponse(
        access_token=token,
        token=token,
        token_type="bearer",
        role=role_name,
        display_name=display_name,
        must_reset_password=user.must_reset_password,
    )


@router.get("/me", response_model=UserProfile)
def me(current_user: User = Depends(get_current_user)):
    return UserProfile(
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.role.name,
        display_name=current_user.role.display_name,
        is_active=current_user.is_active,
    )
