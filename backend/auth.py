import uuid

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
try:
    from passlib.context import CryptContext
except Exception:
    CryptContext = None

from models import Token, User
from database import get_db


# Password hashing context (optional dependency)
if CryptContext is not None:
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
else:
    pwd_context = None


def hash_password(password: str) -> str:
    if pwd_context is not None:
        return pwd_context.hash(password)
    # fallback: no hashing (insecure) — allows the app to run without passlib
    return password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if pwd_context is not None:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
    # fallback: compare plaintext (insecure)
    return plain_password == hashed_password


def login_user(db: Session, username: str, password: str):
    user = db.query(User).options(joinedload(User.role)).filter(User.username == username).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token_value = str(uuid.uuid4())
    token_row = Token(token=token_value, user_id=user.user_id)
    db.add(token_row)
    db.commit()
    return {
        "token": token_value,
        "username": user.username,
        "role": user.role.name,
    }


def get_current_user(authorization: str | None, db: Session):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token_value = authorization.split(" ", 1)[1]
    token_row = db.query(Token).filter(Token.token == token_value).first()
    if not token_row:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).options(joinedload(User.role)).filter(User.user_id == token_row.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_user_dep(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    return get_current_user(authorization, db)


def require_role(*allowed_roles: str):
    def _dependency(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
        user = get_current_user(authorization, db)
        role_name = user.role.name if user.role else None
        if role_name not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return _dependency
