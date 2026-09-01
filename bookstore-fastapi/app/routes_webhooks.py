import os
import hmac
import hashlib
import json
import uuid
import datetime
from fastapi import APIRouter, Request, HTTPException

from . import db, settings_store

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request):
    settings = settings_store.read_settings()
    import stripe
    stripe.api_key = settings.get("stripeSecretKey") or os.environ.get("STRIPE_SECRET_KEY")
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    webhook_secret = settings.get("stripeWebhookSecret") or os.environ.get("STRIPE_WEBHOOK_SECRET")
    try:
        event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook Error: {e}")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata") or {}
        order_id = metadata.get("orderId")
        user_id = metadata.get("userId")

        if order_id:
            db.update("orders", lambda o: o["id"] == order_id,
                       {"status": "paid", "paidAt": datetime.datetime.utcnow().isoformat()})
        elif user_id:
            db.insert("subscriptions", {
                "id": str(uuid.uuid4()),
                "userId": user_id,
                "status": "active",
                "stripeSubscriptionId": session.get("subscription"),
                "stripeCustomerId": session.get("customer"),
                "createdAt": datetime.datetime.utcnow().isoformat(),
            })

    if event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        db.update("subscriptions", lambda s: s.get("stripeSubscriptionId") == sub["id"],
                   {"status": "canceled", "canceledAt": datetime.datetime.utcnow().isoformat()})

    return {"received": True}


def _sort_keys(obj):
    if isinstance(obj, list):
        return [_sort_keys(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _sort_keys(obj[k]) for k in sorted(obj.keys())}
    return obj


@router.post("/nowpayments")
async def nowpayments_webhook(request: Request):
    body = await request.json()
    settings = settings_store.read_settings()
    secret = settings.get("nowpaymentsIpnSecret") or os.environ.get("NOWPAYMENTS_IPN_SECRET")
    if secret:
        sig = request.headers.get("x-nowpayments-sig", "")
        sorted_json = json.dumps(_sort_keys(body), separators=(",", ":"))
        expected = hmac.new(secret.encode(), sorted_json.encode(), hashlib.sha512).hexdigest()
        if sig != expected:
            raise HTTPException(status_code=401, detail="Invalid signature.")

    order_id = body.get("order_id")
    status = body.get("payment_status")
    if order_id and status in ("finished", "confirmed"):
        order = db.find("orders", lambda o: o["id"] == order_id)
        db.update("orders", lambda o: o["id"] == order_id,
                   {"status": "paid", "paidAt": datetime.datetime.utcnow().isoformat()})
        if order and order.get("type") == "subscription":
            db.insert("subscriptions", {
                "id": str(uuid.uuid4()),
                "userId": order["userId"],
                "status": "active",
                "method": "crypto",
                "createdAt": datetime.datetime.utcnow().isoformat(),
            })
    if order_id and status in ("failed", "expired", "refunded"):
        db.update("orders", lambda o: o["id"] == order_id, {"status": status})

    return {"received": True}
