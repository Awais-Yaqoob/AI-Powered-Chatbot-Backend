"""
Onboarding API
GET  /api/v1/onboarding/verify      — ping WordPress site to confirm plugin installed
GET  /api/v1/onboarding/job-stream  — SSE stream for live indexing progress
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import asyncio
import json

from core.auth import require_site
from core.database import get_supabase

router = APIRouter()


@router.get("/verify")
async def verify_connection(site: dict = Depends(require_site)):
    """
    Pings the WordPress site's REST API to confirm
    the plugin is installed and responding.
    """
    test_url = site["site_url"].rstrip("/") + "/wp-json/wp-ai-chatbot/v1/ping"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(test_url)
            if r.status_code == 200:
                return {"status": "connected", "site_url": site["site_url"]}
            else:
                return {"status": "error", "detail": f"Plugin returned HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/job-stream/{job_id}")
async def job_stream(job_id: str, site: dict = Depends(require_site)):
    """
    Server-Sent Events stream — frontend polls this for live
    indexing progress without requiring WebSocket setup.
    """
    async def event_generator():
        db = get_supabase()
        last_chunks = -1

        for _ in range(120):  # max 2 min polling
            result = db.table("indexing_jobs") \
                .select("status, pages_found, pages_indexed, chunks_created, error_message") \
                .eq("id", job_id) \
                .eq("site_id", site["id"]) \
                .single() \
                .execute()

            if not result.data:
                break

            job = result.data
            if job["chunks_created"] != last_chunks:
                last_chunks = job["chunks_created"]
                payload = json.dumps({
                    "status":        job["status"],
                    "pages_found":   job["pages_found"] or 0,
                    "pages_indexed": job["pages_indexed"] or 0,
                    "chunks_created":job["chunks_created"] or 0,
                    "error":         job.get("error_message"),
                })
                yield f"data: {payload}\n\n"

            if job["status"] in ("completed", "failed"):
                yield "data: {\"done\": true}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
