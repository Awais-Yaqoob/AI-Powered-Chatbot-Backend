"""
Authentication - validates WordPress site API keys
"""
from fastapi import Header, HTTPException, status
from core.database import get_site_by_api_key


async def require_site(x_api_key: str = Header(...)) -> dict:
    """
    FastAPI dependency — validates X-Api-Key header.
    Returns site config dict if valid, raises 401 otherwise.
    Usage: site = Depends(require_site)
    """
    site = await get_site_by_api_key(x_api_key)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )
    return site
