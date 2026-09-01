import os
import re
import uuid
import datetime
import requests
from fastapi import APIRouter, HTTPException, Depends

from . import db, settings_store
from .auth import current_user

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

APP_URL = os.environ.get("APP_URL", "http://localhost:8000")


def _stripe():
    settings = settings_store.read_settings()
    if not settings.get("cardEnabled"):
        raise HTTPException(status_code=503, detail="Card payments are not enabled yet. Turn them on from the admin Site tab.")
    key = settings.get("stripeSecretKey") or os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="Card payments are missing a Stripe secret key. Add one from the admin Site tab.")
    import stripe
    stripe.api_key = key
    return stripe


def _nowpayments_key():
    settings = settings_store.read_settings()
    if not settings.get("cryptoEnabled"):
        raise HTTPException(status_code=503, detail="Crypto payments are not enabled yet. Turn them on from the admin Site tab.")
    key = settings.get("nowpaymentsApiKey") or os.environ.get("NOWPAYMENTS_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="Crypto payments are missing a NOWPayments API key. Add one from the admin Site tab.")
    return key


@router.post("/card/book/{book_id}")
def checkout_card_book(book_id: str, current: dict = Depends(current_user)):
    stripe = _stripe()
    book = db.find("books", lambda b: b["id"] == book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")

    order_id = str(uuid.uuid4())
    db.insert("orders", {
        "id": order_id,
        "userId": current["id"],
        "bookId": book["id"],
        "type": "book",
        "method": "card",
        "status": "pending",
        "amount": book["priceCents"],
        "currency": "usd",
        "createdAt": datetime.datetime.utcnow().isoformat(),
    })

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": book["title"]},
                "unit_amount": book["priceCents"],
            },
            "quantity": 1,
        }],
        metadata={"orderId": order_id, "bookId": book["id"], "userId": current["id"]},
        success_url=f"{APP_URL}/order-success?order={order_id}",
        cancel_url=f"{APP_URL}/books/{book['id']}",
    )
    return {"checkoutUrl": session.url}


@router.post("/card/subscription")
def checkout_card_subscription(current: dict = Depends(current_user)):
    stripe = _stripe()
    settings = settings_store.read_settings()
    price_id = settings.get("stripeSubscriptionPriceId") or os.environ.get("STRIPE_SUBSCRIPTION_PRICE_ID")
    if not price_id:
        raise HTTPException(status_code=503, detail="Subscription plan is not configured yet. Add a Stripe subscription price ID from the admin Site tab.")

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        metadata={"userId": current["id"]},
        success_url=f"{APP_URL}/account?sub=success",
        cancel_url=f"{APP_URL}/pricing",
    )
    return {"checkoutUrl": session.url}


@router.post("/crypto/subscription")
def checkout_crypto_subscription(current: dict = Depends(current_user)):
    api_key = _nowpayments_key()
    settings = settings_store.read_settings()
    label = settings.get("subscriptionPriceLabel", "")
    match = re.search(r"[\d.]+", label)
    if not match:
        raise HTTPException(status_code=503, detail="The subscription price isn't set up correctly. Fix it from the admin Site tab.")
    price_amount = float(match.group())

    order_id = str(uuid.uuid4())
    db.insert("orders", {
        "id": order_id,
        "userId": current["id"],
        "bookId": None,
        "type": "subscription",
        "method": "crypto",
        "status": "pending",
        "amount": int(round(price_amount * 100)),
        "currency": "usd",
        "createdAt": datetime.datetime.utcnow().isoformat(),
    })

    resp = requests.post(
        "https://api.nowpayments.io/v1/invoice",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json={
            "price_amount": price_amount,
            "price_currency": "usd",
            "order_id": order_id,
            "order_description": "Premium membership",
            "ipn_callback_url": f"{APP_URL}/api/webhooks/nowpayments",
            "success_url": f"{APP_URL}/account?sub=success",
            "cancel_url": f"{APP_URL}/pricing",
        },
        timeout=15,
    )
    invoice = resp.json()
    if not resp.ok:
        raise HTTPException(status_code=502, detail={"error": "Could not create crypto invoice.", "details": invoice})

    db.update("orders", lambda o: o["id"] == order_id, {"paymentId": invoice.get("id")})
    return {"checkoutUrl": invoice.get("invoice_url")}
@router.post("/crypto/book/{book_id}")
def checkout_crypto_book(book_id: str, current: dict = Depends(current_user)):
    api_key = _nowpayments_key()
    book = db.find("books", lambda b: b["id"] == book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")

    order_id = str(uuid.uuid4())
    db.insert("orders", {
        "id": order_id,
        "userId": current["id"],
        "bookId": book["id"],
        "type": "book",
        "method": "crypto",
        "status": "pending",
        "amount": book["priceCents"],
        "currency": "usd",
        "createdAt": datetime.datetime.utcnow().isoformat(),
    })

    resp = requests.post(
        "https://api.nowpayments.io/v1/invoice",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json={
            "price_amount": book["priceCents"] / 100,
            "price_currency": "usd",
            "order_id": order_id,
            "order_description": book["title"],
            "ipn_callback_url": f"{APP_URL}/api/webhooks/nowpayments",
            "success_url": f"{APP_URL}/order-success?order={order_id}",
            "cancel_url": f"{APP_URL}/books/{book['id']}",
        },
        timeout=15,
    )
    invoice = resp.json()
    if not resp.ok:
        raise HTTPException(status_code=502, detail={"error": "Could not create crypto invoice.", "details": invoice})

    db.update("orders", lambda o: o["id"] == order_id, {"paymentId": invoice.get("id")})
    return {"checkoutUrl": invoice.get("invoice_url")}
