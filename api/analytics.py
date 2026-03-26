"""
Analytics API - usage metrics per site
GET /api/v1/analytics/summary
GET /api/v1/analytics/popular-queries
"""
from fastapi import APIRouter, Depends
from core.auth import require_site
from core.database import get_supabase

router = APIRouter()


@router.get("/summary")
async def analytics_summary(
    days: int = 30,
    site: dict = Depends(require_site),
):
    """Total conversations, tokens, response times for last N days."""
    db = get_supabase()
    result = db.table("conversations") \
        .select("tokens_used, response_time_ms, used_global_fallback, had_disclaimer, flagged_keyword, created_at") \
        .eq("site_id", site["id"]) \
        .gte("created_at", f"now() - interval '{days} days'") \
        .execute()

    rows = result.data or []
    total = len(rows)
    if total == 0:
        return {"total_conversations": 0}

    avg_tokens = sum(r["tokens_used"] or 0 for r in rows) / total
    avg_ms = sum(r["response_time_ms"] or 0 for r in rows) / total
    fallbacks = sum(1 for r in rows if r["used_global_fallback"])
    crisis_flags = sum(1 for r in rows if r["flagged_keyword"])

    return {
        "total_conversations": total,
        "avg_tokens_per_chat": round(avg_tokens, 1),
        "avg_response_ms": round(avg_ms),
        "global_fallback_count": fallbacks,
        "crisis_flags": crisis_flags,
        "period_days": days,
    }


@router.get("/popular-queries")
async def popular_queries(
    limit: int = 20,
    site: dict = Depends(require_site),
):
    """Return recent unanswered or most common questions."""
    db = get_supabase()
    result = db.table("conversations") \
        .select("user_message, bot_response, created_at") \
        .eq("site_id", site["id"]) \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()
    return result.data or []
