from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import User
from schemas import LoginRequest, LoginResponse, UserProfile
from security import create_access_token

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username, User.password == payload.password).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    role_name = user.role.name
    display_name = user.role.display_name
    token = create_access_token(subject=user.username, role=role_name)
    return LoginResponse(access_token=token, token=token, token_type="bearer", role=role_name, display_name=display_name)


@router.get("/me", response_model=UserProfile)
def me(current_user: User = Depends(get_current_user)):
    return UserProfile(
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.role.name,
        display_name=current_user.role.display_name,
        is_active=current_user.is_active,
    )
