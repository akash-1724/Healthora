from fastapi import Depends, FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from auth import get_current_user, login_user
from database import Base, SessionLocal, engine, get_db
from models import Role, User
from inventory import router as inventory_router
from users import router as users_router

app = FastAPI(title="Healthora Minimal Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)

        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            db.add(User(username="admin", password="admin123", role_id=admin_role.id, is_active=True))
            db.commit()
    finally:
        db.close()


@app.get("/")
def home():
    return {"message": "Healthora backend running"}


@app.post("/api/login")
def login(payload: dict, db: Session = Depends(get_db)):
    return login_user(db, payload.get("username", ""), payload.get("password", ""))


@app.get("/api/me")
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role_id": user.role_id,
        "is_active": user.is_active,
        "created_at": user.created_at,
    }


app.include_router(users_router)
app.include_router(inventory_router)
