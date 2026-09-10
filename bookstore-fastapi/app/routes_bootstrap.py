"""
TEMPORARY: lets you (re)set an admin login on the live site without shell
access to Railway. Protected by a secret only you know (BOOTSTRAP_SECRET
env var on Railway) — remove this file once you're back in, since leaving
a password-reset endpoint live is not something to keep around long-term.
"""
import os
import uuid
import datetime
import bcrypt
from fastapi import APIRouter, HTTPException
from . import db

router = APIRouter(prefix="/api", tags=["bootstrap"])


@router.get("/bootstrap-admin")
def bootstrap_admin(secret: str, email: str, password: str, name: str = "Admin"):
    expected = os.environ.get("BOOTSTRAP_SECRET")
    if not expected or secret != expected:
        raise HTTPException(status_code=403, detail="Invalid secret.")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    existing = db.find("users", lambda u: u["email"].lower() == email.lower())

    if existing:
        db.update("users", lambda u: u["id"] == existing["id"], {"passwordHash": password_hash, "role": "admin"})
        return {"ok": True, "action": "password reset on existing account"}

    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": name,
        "country": "",
        "passwordHash": password_hash,
        "role": "admin",
        "createdAt": datetime.datetime.utcnow().isoformat(),
    }
    db.insert("users", user)
    return {"ok": True, "action": "new admin account created"}
