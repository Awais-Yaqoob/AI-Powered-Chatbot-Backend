"""
Sites API - site registration and management
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.database import get_supabase
import uuid

router = APIRouter()


class RegisterSiteRequest(BaseModel):
    site_url: str
    site_name: str
    site_type: str = "general"
    plan: str = "starter"


@router.post("/register")
async def register_site(request: RegisterSiteRequest):
    """
    Register a new WordPress site.
    Returns API key to store in WordPress plugin settings.
    """
    db = get_supabase()
    api_key = str(uuid.uuid4()).replace("-", "")

    result = db.table("sites").insert({
        "site_url": request.site_url.rstrip("/"),
        "site_name": request.site_name,
        "site_type": request.site_type,
        "plan": request.plan,
        "api_key": api_key,
    }).execute()

    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to register site")

    return {
        "site_id": result.data[0]["id"],
        "api_key": api_key,
        "message": "Site registered. Save your API key — it won't be shown again.",
    }


@router.get("/info")
async def get_site_info(api_key: str):
    """Get site info by API key."""
    db = get_supabase()
    result = db.table("sites").select(
        "id, site_url, site_name, site_type, plan, llm_model, indexed_at, created_at"
    ).eq("api_key", api_key).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Site not found")
    return result.data
