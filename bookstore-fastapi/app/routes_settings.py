from fastapi import APIRouter
from . import settings_store

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    return {"settings": settings_store.public_settings()}
