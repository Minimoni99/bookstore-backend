"""
Usage: python create_admin.py you@email.com yourPassword123
"""
import sys
import os
import uuid
import datetime
import bcrypt

sys.path.insert(0, os.path.dirname(__file__))
from app import db  # noqa: E402


def main():
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py you@email.com yourPassword123")
        sys.exit(1)
    email, password = sys.argv[1], sys.argv[2]

    existing = db.find("users", lambda u: u["email"].lower() == email.lower())
    if existing:
        db.update("users", lambda u: u["id"] == existing["id"], {"role": "admin"})
        print(f"Existing user {email} promoted to admin.")
        return

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db.insert("users", {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": "Admin",
        "passwordHash": password_hash,
        "role": "admin",
        "createdAt": datetime.datetime.utcnow().isoformat(),
    })
    print(f"Admin account created: {email}")


if __name__ == "__main__":
    main()
