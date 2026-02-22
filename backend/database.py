import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv

# Load .env from the project root (one level above the backend/ folder)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://healthora_user:healthora_password@db:5432/healthora",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
