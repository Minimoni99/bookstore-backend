import sys
import os
import uuid
import datetime

sys.path.insert(0, os.path.dirname(__file__))
from app import db  # noqa: E402

books = db.read_all("books")
if not books:
    db.insert("books", {
        "id": str(uuid.uuid4()),
        "title": "Sample Title",
        "penName": "Your Pen Name",
        "priceCents": 299,
        "description": "Replace this with your real book description from the admin panel.",
        "coverUrl": "",
        "downloadUrl": "https://example.com/replace-with-real-file-link.epub",
        "createdAt": datetime.datetime.utcnow().isoformat(),
    })
    print("Seeded one sample book.")
else:
    print("Books already exist — skipping seed.")
