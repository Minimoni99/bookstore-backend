"""
Marketing-capture leads — replaces customer accounts entirely. Visitors
fill in name/email/country on the /apply flow (no password, no login);
the admin sees them under the Users tab and reaches out manually.
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


@admin_router.get("/leads")
def list_leads():
    leads = db.read_all("leads")
    leads.sort(key=lambda l: l.get("createdAt", ""), reverse=True)
    return {"leads": leads}


@admin_router.get("/leads/stats")
def leads_stats():
    leads = db.read_all("leads")
    requested = [l for l in leads if l.get("requestedAccess")]
    by_channel = {"email": 0, "whatsapp": 0, "telegram": 0}
    for l in requested:
        c = l.get("channel")
        if c in by_channel:
            by_channel[c] += 1
    recent = sorted(leads, key=lambda l: l.get("createdAt", ""), reverse=True)[:10]
    return {
        "totalLeads": len(leads),
        "totalRequestedAccess": len(requested),
        "byChannel": by_channel,
        "recent": recent,
    }
