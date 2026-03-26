import os
import logging
from contextlib import asynccontextmanager
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from auth import router as auth_router
from ai_report import router as ai_report_router
from audit_router import router as audit_log_router
from dashboard import router as dashboard_router
from database import SessionLocal
from inventory import router as inventory_router
from models import DrugBatch
from notifications import router as notifications_router
from prescriptions import router as prescriptions_router
from purchase_orders import router as purchase_orders_router
from reorder_recommendation import router as reorder_recommendation_router
from seed import seed_all
from suppliers import router as suppliers_router
from users import router as users_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("healthora")

# ─── Rate limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ─── Background scheduler: auto-expire batches ────────────────────────────────
scheduler = BackgroundScheduler()


def auto_expire_batches():
    """Mark all drug batches past their expiry date as expired."""
    db = SessionLocal()
    try:
        today = date.today()
        expired = db.query(DrugBatch).filter(DrugBatch.expiry_date < today, DrugBatch.is_expired.is_(False)).all()
        if expired:
            for batch in expired:
                batch.is_expired = True
            db.commit()
            logger.info("Auto-expired %d drug batches", len(expired))
    except Exception:
        logger.exception("Error in auto_expire_batches job")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if os.getenv("ENABLE_STARTUP_SEED", "true").lower() == "true":
        seed_fail_open = os.getenv("SEED_FAIL_OPEN", "true").lower() == "true"
        db = SessionLocal()
        try:
            seed_all(db)
        except Exception:
            logger.exception("Startup seeding failed")
            if not seed_fail_open:
                raise
            logger.warning("Continuing startup because SEED_FAIL_OPEN=true")
        finally:
            db.close()

    auto_expire_batches()
    scheduler.add_job(auto_expire_batches, "cron", hour=0, minute=5)  # Run at 00:05 every day
    scheduler.start()
    logger.info("Healthora backend started")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    logger.info("Healthora backend stopped")


app = FastAPI(title="Healthora Backend", version="1.0.0", lifespan=lifespan)

# ─── CORS ─────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX", r"https?://(localhost|127\.0\.0\.1)(:\d+)?")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Rate limiter error handler ───────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/")
def home():
    return {"message": "Healthora backend running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(inventory_router)
app.include_router(dashboard_router)
app.include_router(prescriptions_router)
app.include_router(suppliers_router)
app.include_router(purchase_orders_router)
app.include_router(notifications_router)
app.include_router(audit_log_router)
app.include_router(ai_report_router)
app.include_router(reorder_recommendation_router)
