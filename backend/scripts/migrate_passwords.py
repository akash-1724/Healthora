from database import SessionLocal
from models import User
from auth import hash_password


def main():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        updated = 0
        for u in users:
            pw = (u.password or "")
            # naive check: bcrypt hashes start with $2
            if pw and not pw.startswith("$2"):
                u.password = hash_password(pw)
                db.add(u)
                updated += 1
        if updated:
            db.commit()
        print(f"Updated {updated} user password(s)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
