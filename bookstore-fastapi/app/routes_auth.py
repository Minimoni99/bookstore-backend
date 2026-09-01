import uuid
import datetime
import bcrypt
from fastapi import APIRouter, HTTPException, Depends

from . import db
from .auth import sign, current_user
from .schemas import RegisterBody, LoginBody, ProfileUpdate, PasswordChange

router = APIRouter(prefix="/api/auth", tags=["auth"])


def safe_user(u: dict) -> dict:
    return {"id": u["id"], "email": u["email"], "name": u.get("name", ""), "role": u["role"]}


@router.post("/register")
def register(body: RegisterBody):
    if db.find("users", lambda u: u["email"].lower() == body.email.lower()):
        raise HTTPException(status_code=409, detail="An account with that email already exists.")

    password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = {
        "id": str(uuid.uuid4()),
        "email": body.email,
        "name": body.name or "",
        "passwordHash": password_hash,
        "role": "customer",  # first admin is created via create_admin.py
        "createdAt": datetime.datetime.utcnow().isoformat(),
    }
    db.insert("users", user)
    return {"token": sign(user), "user": safe_user(user)}


@router.post("/login")
def login(body: LoginBody):
    user = db.find("users", lambda u: u["email"].lower() == body.email.lower())
    if not user or not bcrypt.checkpw(body.password.encode(), user["passwordHash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {"token": sign(user), "user": safe_user(user)}


@router.get("/me")
def me(current: dict = Depends(current_user)):
    user = db.find("users", lambda u: u["id"] == current["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    orders = db.filter_rows("orders", lambda o: o["userId"] == user["id"])
    subscriptions = db.filter_rows("subscriptions", lambda s: s["userId"] == user["id"])
    return {"user": safe_user(user), "orders": orders, "subscriptions": subscriptions}


@router.put("/me")
def update_profile(body: ProfileUpdate, current: dict = Depends(current_user)):
    user = db.find("users", lambda u: u["id"] == current["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    patch = {}
    if body.name is not None:
        patch["name"] = body.name
    if body.email is not None and body.email.lower() != user["email"].lower():
        if db.find("users", lambda u: u["email"].lower() == body.email.lower() and u["id"] != user["id"]):
            raise HTTPException(status_code=409, detail="That email is already in use.")
        patch["email"] = body.email

    updated = db.update("users", lambda u: u["id"] == user["id"], patch) if patch else user
    return {"user": safe_user(updated), "token": sign(updated)}


@router.post("/change-password")
def change_password(body: PasswordChange, current: dict = Depends(current_user)):
    user = db.find("users", lambda u: u["id"] == current["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if not bcrypt.checkpw(body.currentPassword.encode(), user["passwordHash"].encode()):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    if len(body.newPassword) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters.")

    new_hash = bcrypt.hashpw(body.newPassword.encode(), bcrypt.gensalt()).decode()
    db.update("users", lambda u: u["id"] == user["id"], {"passwordHash": new_hash})
    return {"ok": True}
