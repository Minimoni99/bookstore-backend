"""
Marketing-capture leads — replaces customer accounts entirely. Visitors
fill in name/email/country on the /apply flow (no password, no login);
the admin sees them under the Users tab and reaches out manually.

Every submission and every access-request is stored as its own event so
nothing is lost, but the admin-facing views always group by email so the
same person never shows up as duplicate rows — instead each row carries
a count of how many times they've submitted and how many times they've
requested access.
"""
import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException
from .schemas import LeadBody, RequestAccessBody
from .auth import current_admin
from . import db

router = APIRouter(prefix="/api", tags=["leads"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(current_admin)])


@router.post("/leads")
def create_lead(body: LeadBody):
    lead = {
        "id": str(uuid.uuid4()),
        "firstName": body.firstName,
        "surname": body.surname,
        "email": body.email,
        "country": body.country,
        "createdAt": datetime.datetime.utcnow().isoformat(),
        "requestedAccess": False,
        "channel": None,
        "requestedAt": None,
    }
    db.insert("leads", lead)
    return {"lead": lead}


@router.patch("/leads/{lead_id}/request-access")
def request_access(lead_id: str, body: RequestAccessBody):
    if body.channel not in ("email", "whatsapp", "telegram"):
        raise HTTPException(status_code=400, detail="channel must be email, whatsapp, or telegram.")
    updated = db.update(
        "leads",
        lambda l: l["id"] == lead_id,
        {"requestedAccess": True, "channel": body.channel, "requestedAt": datetime.datetime.utcnow().isoformat()},
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return {"lead": updated}


def _aggregate_by_email(leads: list) -> list:
    """Collapse raw submission/request events into one row per email,
    most-recently-active first, each carrying how many times that person
    has submitted and how many times they've requested access."""
    groups = {}
    for l in leads:
        key = l["email"].lower()
        g = groups.setdefault(key, {
            "email": l["email"],
            "firstName": l["firstName"],
            "surname": l["surname"],
            "country": l["country"],
            "timesEntered": 0,
            "timesRequestedAccess": 0,
            "lastChannel": None,
            "lastSubmittedAt": l["createdAt"],
            "lastRequestedAt": None,
        })
        g["timesEntered"] += 1
        # Keep the most recent submission's name/country/timestamp as the
        # display values, since people's names rarely change but this is
        # the freshest info we have.
        if l["createdAt"] >= g["lastSubmittedAt"]:
            g["firstName"] = l["firstName"]
            g["surname"] = l["surname"]
            g["country"] = l["country"]
            g["lastSubmittedAt"] = l["createdAt"]
        if l.get("requestedAccess"):
            g["timesRequestedAccess"] += 1
            requested_at = l.get("requestedAt") or ""
            if g["lastRequestedAt"] is None or requested_at >= g["lastRequestedAt"]:
                g["lastRequestedAt"] = requested_at
                g["lastChannel"] = l.get("channel")

    rows = list(groups.values())
    rows.sort(key=lambda r: r["lastSubmittedAt"], reverse=True)
    return rows


@admin_router.get("/leads")
def list_leads():
    leads = db.read_all("leads")
    return {"leads": _aggregate_by_email(leads)}


@admin_router.get("/leads/stats")
def leads_stats():
    leads = db.read_all("leads")
    rows = _aggregate_by_email(leads)
    requested_rows = [r for r in rows if r["timesRequestedAccess"] > 0]

    by_channel = {"email": 0, "whatsapp": 0, "telegram": 0}
    for r in requested_rows:
        c = r["lastChannel"]
        if c in by_channel:
            by_channel[c] += 1

    return {
        "totalLeads": len(rows),
        "totalRequestedAccess": len(requested_rows),
        "byChannel": by_channel,
        "recent": rows[:10],
    }
