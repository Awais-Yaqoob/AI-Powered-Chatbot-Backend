"""
Supabase client - database access layer
"""
from supabase import create_client, Client
from core.config import settings
from functools import lru_cache


@lru_cache()
def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def get_site_by_api_key(api_key: str) -> dict | None:
    """Fetch site config by API key — used for auth on every request."""
    db = get_supabase()
    result = db.table("sites").select("*").eq("api_key", api_key).eq("is_active", True).single().execute()
    return result.data if result.data else None


async def save_conversation(
    site_id: str,
    session_id: str,
    user_message: str,
    bot_response: str,
    matched_chunk_ids: list,
    used_global_fallback: bool,
    had_disclaimer: bool,
    tokens_used: int,
    response_time_ms: int,
    flagged_keyword: str = None,
):
    db = get_supabase()
    db.table("conversations").insert({
        "site_id": site_id,
        "session_id": session_id,
        "user_message": user_message,
        "bot_response": bot_response,
        "matched_chunks": matched_chunk_ids,
        "used_global_fallback": used_global_fallback,
        "had_disclaimer": had_disclaimer,
        "tokens_used": tokens_used,
        "response_time_ms": response_time_ms,
        "flagged_keyword": flagged_keyword,
    }).execute()


# async def semantic_search(site_id: str, embedding: list, top_k: int = 5) -> list:
#     """Run pgvector similarity search for a specific site."""
#     db = get_supabase()
#     result = db.rpc("match_chunks", {
#         "query_embedding": embedding,
#         "match_site_id": site_id,
#         "match_count": top_k,
#         # "similarity_threshold": settings.SIMILARITY_THRESHOLD,
#           "similarity_threshold": 0.0,
#     }).execute()
#      print("Chunks found:", result.data)
#     return result.data or []

async def semantic_search(site_id: str, embedding: list, top_k: int = 5) -> list:
    """Run pgvector similarity search for a specific site."""
    db = get_supabase()
    result = db.rpc("match_chunks", {
        "p_embedding": embedding,       # make sure this matches the RPC
        "p_site_id": site_id,
        "p_count": top_k,
        "p_threshold": 0.0,            # ignore threshold for testing
    }).execute()
    print("Chunks found:", result.data)  # debug
    return result.data or []


async def global_search(embedding: list, top_k: int = 3) -> list:
    """Run pgvector similarity search on global knowledge base."""
    db = get_supabase()
    result = db.rpc("match_global_chunks", {
        "query_embedding": embedding,
        "match_count": top_k,
        "similarity_threshold": settings.GLOBAL_SIMILARITY_THRESHOLD,
    }).execute()
    return result.data or []


async def store_chunks(site_id: str, chunks: list[dict]):
    """Upsert content chunks with embeddings for a site."""
    db = get_supabase()
    # Delete old chunks for this site before re-indexing
    db.table("chunks").delete().eq("site_id", site_id).execute()
    if chunks:
        db.table("chunks").insert(chunks).execute()


async def update_indexing_job(job_id: str, updates: dict):
    db = get_supabase()
    db.table("indexing_jobs").update(updates).eq("id", job_id).execute()


async def create_indexing_job(site_id: str, triggered_by: str = "manual") -> str:
    db = get_supabase()
    result = db.table("indexing_jobs").insert({
        "site_id": site_id,
        "triggered_by": triggered_by,
        "status": "pending",
    }).execute()
    return result.data[0]["id"]
