from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import router as auth_router
from dashboard import router as dashboard_router
from database import SessionLocal
from inventory import router as inventory_router
from seed import seed_all
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
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()


@app.get("/")
def home():
    return {"message": "Healthora backend running"}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(inventory_router)
app.include_router(dashboard_router)
