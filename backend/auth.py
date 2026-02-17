import uuid

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from models import Token, User


def login_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username, User.password == password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token_value = str(uuid.uuid4())
    token_row = Token(token=token_value, user_id=user.user_id)
    db.add(token_row)
    db.commit()
    return {"token": token_value}


def get_current_user(authorization: str | None, db: Session):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token_value = authorization.split(" ", 1)[1]
    token_row = db.query(Token).filter(Token.token == token_value).first()
    if not token_row:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.user_id == token_row.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
