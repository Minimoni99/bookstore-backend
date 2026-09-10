"""
Marketing-capture leads — replaces customer accounts entirely. Visitors
fill in name/email/country on the /apply flow (no password, no login);
the admin sees them under the Users tab and reaches out manually.
"""
import uuid
import datetime
from fastapi import APIRouter, Depends
from .schemas import LeadBody
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
    }
    db.insert("leads", lead)
    return {"lead": lead}


@admin_router.get("/leads")
def list_leads():
    leads = db.read_all("leads")
    leads.sort(key=lambda l: l.get("createdAt", ""), reverse=True)
    return {"leads": leads}
