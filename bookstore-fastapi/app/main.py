import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import routes_auth, routes_books, routes_checkout, routes_webhooks, routes_admin, routes_downloads, routes_settings

app = FastAPI(title="Ebook Store API")

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Allow your Next.js frontend (local dev + your deployed Vercel domain) to call this API.
# Tighten this list before going live.
allowed_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_auth.router)
app.include_router(routes_books.router)
app.include_router(routes_checkout.router)
app.include_router(routes_webhooks.router)
app.include_router(routes_admin.router)
app.include_router(routes_downloads.router)
app.include_router(routes_settings.router)


@app.get("/health")
def health():
    return {"ok": True}
