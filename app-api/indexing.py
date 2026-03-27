"""
Indexing API
- POST /api/v1/index/push     — WordPress plugin pushes content directly
- POST /api/v1/index/scrape   — Backend scrapes the site via Playwright
- GET  /api/v1/index/status   — Check indexing job status
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from datetime import datetime

from core.auth import require_site
from core.database import (
    store_chunks, create_indexing_job,
    update_indexing_job, get_supabase
)
from services.chunker import prepare_chunks_from_pages
from services.embeddings import embed_batch
from services.scraper import scrape_site

router = APIRouter()


class PagePayload(BaseModel):
    url: str
    title: str
    html_content: str
    post_type: str = "page"


class PushIndexRequest(BaseModel):
    pages: list[PagePayload]
    triggered_by: str = "save_post"


class ScrapeIndexRequest(BaseModel):
    max_pages: int = 200


async def _run_indexing(
    site: dict,
    pages: list[dict],
    job_id: str,
    triggered_by: str = "manual"
):
    """Background task — chunks, embeds, and stores content."""
    try:
        await update_indexing_job(job_id, {
            "status": "running",
            "pages_found": len(pages),
            "started_at": datetime.utcnow().isoformat(),
        })

        # Chunk content
        chunks = prepare_chunks_from_pages(pages, site["id"])

        if not chunks:
            await update_indexing_job(job_id, {
                "status": "completed",
                "chunks_created": 0,
                "completed_at": datetime.utcnow().isoformat(),
            })
            return

        # Generate embeddings in batch (cost-efficient)
        texts = [c["content"] for c in chunks]
        embeddings = await embed_batch(texts)

        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        # Store in Supabase (replaces previous index)
        await store_chunks(site["id"], chunks)

        # Update site indexed_at
        get_supabase().table("sites").update({
            "indexed_at": datetime.utcnow().isoformat()
        }).eq("id", site["id"]).execute()

        await update_indexing_job(job_id, {
            "status": "completed",
            "pages_indexed": len(pages),
            "chunks_created": len(chunks),
            "completed_at": datetime.utcnow().isoformat(),
        })

    except Exception as e:
        await update_indexing_job(job_id, {
            "status": "failed",
            "error_message": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        })


@router.post("/push")
async def push_index(
    request: PushIndexRequest,
    background_tasks: BackgroundTasks,
    site: dict = Depends(require_site),
):
    """
    WordPress plugin pushes page content directly.
    Used for incremental updates on save_post hook.
    """
    job_id = await create_indexing_job(site["id"], triggered_by=request.triggered_by)
    pages = [p.model_dump() for p in request.pages]
    background_tasks.add_task(_run_indexing, site, pages, job_id, request.triggered_by)
    return {"job_id": job_id, "status": "queued", "pages": len(pages)}


@router.post("/scrape")
async def scrape_index(
    request: ScrapeIndexRequest,
    background_tasks: BackgroundTasks,
    site: dict = Depends(require_site),
):
    """
    Triggers Playwright crawl of the site.
    Used for initial setup or full re-index.
    """
    async def _scrape_and_index(site, job_id, max_pages):
        pages = await scrape_site(site["site_url"], max_pages=max_pages)
        await _run_indexing(site, pages, job_id, "scrape")

    job_id = await create_indexing_job(site["id"], triggered_by="scrape")
    background_tasks.add_task(_scrape_and_index, site, job_id, request.max_pages)
    return {"job_id": job_id, "status": "queued", "message": "Scraping started in background"}


@router.get("/status/{job_id}")
async def indexing_status(
    job_id: str,
    site: dict = Depends(require_site),
):
    """Poll indexing job status."""
    db = get_supabase()
    result = db.table("indexing_jobs") \
        .select("*") \
        .eq("id", job_id) \
        .eq("site_id", site["id"]) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    return result.data
