from fastapi import Depends, FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from auth import get_current_user, login_user, hash_password
from database import Base, SessionLocal, engine, get_db
from models import InventoryItem, Role, User
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

SEED_INVENTORY = [
    {"name": "Paracetamol", "batch": "P-1001", "expiry": "2026-04-15", "quantity": 240, "price": 12.50},
    {"name": "Amoxicillin", "batch": "A-5620", "expiry": "2026-03-20", "quantity": 130, "price": 18.00},
    {"name": "Cetirizine", "batch": "C-3022", "expiry": "2026-09-10", "quantity": 95, "price": 9.75},
]


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Ensure standard roles exist
        roles_to_ensure = [
            "System Admin",
            "Chief Medical Officer",
            "Pharmacy Manager",
            "Senior Pharmacist",
            "Staff Pharmacist",
            "Inventory Clerk",
        ]
        existing_roles = {str(r.name): r for r in db.query(Role).all()}
        for role_name in roles_to_ensure:
            if role_name not in existing_roles:
                r = Role(name=role_name)
                db.add(r)
        db.commit()

        # Refresh mapping after potential inserts
        existing_roles = {str(r.name): r for r in db.query(Role).all()}

        # Seed admin user (hash password) - use System Admin role
        admin_role = existing_roles.get("System Admin")
        admin_user = db.query(User).filter(User.username == "admin").first()
        if admin_role:
            if not admin_user:
                db.add(User(username="admin", password=hash_password("admin123"), role_id=admin_role.id, is_active=True))
            else:
                # Ensure admin user has System Admin role
                admin_user.role_id = admin_role.id
                db.add(admin_user)
            db.commit()

        # NOTE: existing DB password migration is intentionally skipped here
        # to avoid unexpected edge-cases during startup. If you want an
        # automated migration, run a one-off script to inspect and convert
        # plaintext passwords to hashed values.

        # Seed inventory items
        if db.query(InventoryItem).count() == 0:
            for item in SEED_INVENTORY:
                db.add(InventoryItem(**item))
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
        "role": user.role.name,
        "is_active": user.is_active,
        "created_at": user.created_at,
    }


app.include_router(users_router)
app.include_router(inventory_router)
