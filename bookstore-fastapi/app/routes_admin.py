import uuid
import datetime
import os
import shutil
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File

from . import db
from .auth import current_admin
from .schemas import BookCreate, BookUpdate, RoleUpdate, SettingsUpdate
from . import settings_store

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(current_admin)])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR") or os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8MB


# ---- Books ----
@router.get("/books")
def list_books():
    return {"books": db.read_all("books")}


@router.post("/books")
def create_book(body: BookCreate):
    book = {
        "id": str(uuid.uuid4()),
        "title": body.title,
        "penName": body.penName or "",
        "priceCents": body.priceCents,
        "description": body.description or "",
        "coverUrl": body.coverUrl or "",
        "downloadUrl": body.downloadUrl,  # never sent to non-purchasers — see routes_books.py / routes_downloads.py
        "createdAt": datetime.datetime.utcnow().isoformat(),
    }
    db.insert("books", book)
    return {"book": book}


@router.put("/books/{book_id}")
def update_book(book_id: str, body: BookUpdate):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = db.update("books", lambda b: b["id"] == book_id, patch)
    if not updated:
        raise HTTPException(status_code=404, detail="Book not found.")
    return {"book": updated}


@router.delete("/books/{book_id}")
def delete_book(book_id: str):
    ok = db.remove("books", lambda b: b["id"] == book_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Book not found.")
    return {"deleted": True}


# ---- Video uploads (hero video) ----
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
MAX_VIDEO_UPLOAD_BYTES = 300 * 1024 * 1024  # 300MB


@router.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only MP4, WEBM, or MOV videos are allowed.")

    contents = await file.read()
    if len(contents) > MAX_VIDEO_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Video is too large (max 300MB). Export at 1080p with reasonable bitrate.")

    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    return {"url": f"/uploads/{filename}"}


# ---- Image uploads (book covers, author photo) ----
@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, WEBP, or GIF images are allowed.")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Image is too large (max 8MB).")

    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    # main.py mounts /uploads as a static folder pointing at this same directory.
    return {"url": f"/uploads/{filename}"}


# ---- Orders ----
@router.get("/orders")
def list_orders():
    orders = db.read_all("orders")
    books = db.read_all("books")
    users = db.read_all("users")
    book_titles = {b["id"]: b["title"] for b in books}
    user_emails = {u["id"]: u["email"] for u in users}
    enriched = [
        {**o, "bookTitle": book_titles.get(o.get("bookId")), "userEmail": user_emails.get(o.get("userId"))}
        for o in orders
    ]
    return {"orders": enriched}


# ---- Subscriptions ----
@router.get("/subscriptions")
def list_subscriptions():
    subs = db.read_all("subscriptions")
    users = db.read_all("users")
    user_emails = {u["id"]: u["email"] for u in users}
    enriched = [{**s, "userEmail": user_emails.get(s.get("userId"))} for s in subs]
    return {"subscriptions": enriched}


# ---- Users ----
@router.get("/users")
def list_users():
    users = [{k: v for k, v in u.items() if k != "passwordHash"} for u in db.read_all("users")]
    return {"users": users}


@router.put("/users/{user_id}/role")
def set_role(user_id: str, body: RoleUpdate):
    if body.role not in ("customer", "admin"):
        raise HTTPException(status_code=400, detail="role must be customer or admin.")
    updated = db.update("users", lambda u: u["id"] == user_id, {"role": body.role})
    if not updated:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"ok": True}


# ---- Dashboard ----
def _period_start(period: str) -> datetime.datetime:
    now = datetime.datetime.utcnow()
    if period == "day":
        return now - datetime.timedelta(hours=24)
    if period == "week":
        return now - datetime.timedelta(days=7)
    if period == "month":
        return now - datetime.timedelta(days=30)
    return datetime.datetime.min  # "all"


def _parse_dt(s: str) -> datetime.datetime:
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        return datetime.datetime.min


@router.get("/dashboard")
def dashboard(period: str = "month"):
    if period not in ("day", "week", "month", "all"):
        raise HTTPException(status_code=400, detail="period must be day, week, month, or all.")

    start = _period_start(period)
    users = db.read_all("users")
    orders = db.read_all("orders")
    books = db.read_all("books")
    subs = db.read_all("subscriptions")

    customers = [u for u in users if u.get("role") != "admin"]
    active_premium_ids = {s["userId"] for s in subs if s.get("status") == "active"}
    premium_count = sum(1 for u in customers if u["id"] in active_premium_ids)
    regular_count = len(customers) - premium_count

    def in_period(dt_str):
        return _parse_dt(dt_str) >= start

    paid_orders_in_period = [o for o in orders if o.get("status") == "paid" and in_period(o.get("paidAt") or o.get("createdAt", ""))]
    income_cents = sum(o.get("amount", 0) for o in paid_orders_in_period)
    book_orders_in_period = [o for o in paid_orders_in_period if o.get("type") == "book"]
    new_users_in_period = [u for u in customers if in_period(u.get("createdAt", ""))]
    new_regular = sum(1 for u in new_users_in_period if u["id"] not in active_premium_ids)
    new_premium = len(new_users_in_period) - new_regular

    # Top books by paid-order count within the period
    book_titles = {b["id"]: b["title"] for b in books}
    tally = {}
    for o in book_orders_in_period:
        bid = o.get("bookId")
        if not bid:
            continue
        tally.setdefault(bid, {"count": 0, "revenue": 0})
        tally[bid]["count"] += 1
        tally[bid]["revenue"] += o.get("amount", 0)
    top_books = sorted(
        [{"title": book_titles.get(bid, "Unknown"), "sold": v["count"], "revenueCents": v["revenue"]} for bid, v in tally.items()],
        key=lambda r: r["sold"], reverse=True
    )[:5]

    # Chart buckets: daily for day/week/month, monthly for all
    now = datetime.datetime.utcnow()
    buckets = []
    if period == "all":
        # last 12 months
        for i in range(11, -1, -1):
            month_start = (now.replace(day=1) - datetime.timedelta(days=30 * i)).replace(day=1)
            month_end = (month_start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            total = sum(o.get("amount", 0) for o in orders
                        if o.get("status") == "paid" and month_start <= _parse_dt(o.get("paidAt") or o.get("createdAt", "")) < month_end)
            buckets.append(total / 100)
    else:
        days_back = {"day": 1, "week": 7, "month": 30}[period]
        # "day" gets 24 hourly buckets, others get daily buckets
        if period == "day":
            for i in range(23, -1, -1):
                bucket_start = now - datetime.timedelta(hours=i + 1)
                bucket_end = now - datetime.timedelta(hours=i)
                total = sum(o.get("amount", 0) for o in orders
                            if o.get("status") == "paid" and bucket_start <= _parse_dt(o.get("paidAt") or o.get("createdAt", "")) < bucket_end)
                buckets.append(total / 100)
        else:
            for i in range(days_back - 1, -1, -1):
                bucket_start = (now - datetime.timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
                bucket_end = bucket_start + datetime.timedelta(days=1)
                total = sum(o.get("amount", 0) for o in orders
                            if o.get("status") == "paid" and bucket_start <= _parse_dt(o.get("paidAt") or o.get("createdAt", "")) < bucket_end)
                buckets.append(total / 100)

    return {
        "totalUsers": len(customers),
        "regularCount": regular_count,
        "premiumCount": premium_count,
        "incomeCents": income_cents,
        "booksSold": len(book_orders_in_period),
        "distinctTitlesSold": len(tally),
        "newUsers": len(new_users_in_period),
        "newRegular": new_regular,
        "newPremium": new_premium,
        "topBooks": top_books,
        "chart": buckets,
    }


# ---- Site settings (homepage hero + author bio/photo) ----
@router.get("/settings")
def get_settings_admin():
    return {"settings": settings_store.read_settings()}


@router.put("/settings")
def update_settings(body: SettingsUpdate):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = settings_store.write_settings(patch)
    return {"settings": updated}
