from fastapi import APIRouter, HTTPException
from . import db

router = APIRouter(prefix="/api/books", tags=["books"])


def public_book(b: dict) -> dict:
    return {k: v for k, v in b.items() if k != "downloadUrl"}


@router.get("")
def list_books():
    return {"books": [public_book(b) for b in db.read_all("books")]}


@router.get("/{book_id}")
def get_book(book_id: str):
    book = db.find("books", lambda b: b["id"] == book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")
    return {"book": public_book(book)}
