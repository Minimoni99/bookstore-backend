from fastapi import APIRouter, HTTPException, Depends

from . import db
from .auth import current_user

router = APIRouter(prefix="/api/downloads", tags=["downloads"])


@router.get("/{book_id}")
def get_download(book_id: str, current: dict = Depends(current_user)):
    book = db.find("books", lambda b: b["id"] == book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")

    paid_order = db.find(
        "orders",
        lambda o: o["userId"] == current["id"] and o["bookId"] == book_id and o["status"] == "paid",
    )
    active_sub = db.find(
        "subscriptions",
        lambda s: s["userId"] == current["id"] and s["status"] == "active",
    )

    if not paid_order and not active_sub:
        raise HTTPException(status_code=403, detail="You don't have access to this book yet.")

    # downloadUrl can point at a signed S3/R2 URL, a local file, etc.
    return {"downloadUrl": book["downloadUrl"]}
