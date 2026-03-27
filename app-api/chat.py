"""
Chat API — Core RAG pipeline
POST /api/v1/chat/message
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import time
import uuid

from core.auth import require_site
from core.database import semantic_search, global_search, save_conversation
from services.embeddings import embed_text
from services.llm import generate_answer
from services.safety import detect_crisis, get_disclaimer, get_crisis_response, apply_disclaimer

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    conversation_history: list | None = None  # [{role, content}, ...]


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    used_fallback: bool = False
    had_disclaimer: bool = False
    crisis_detected: bool = False


@router.post("/message", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    site: dict = Depends(require_site),
):
    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())
    site_id = site["id"]
    site_type = site.get("site_type", "general")

    # ── 1. Crisis detection ─────────────────────────────────
    flagged_keyword = detect_crisis(request.message)
    if flagged_keyword:
        crisis_response = get_crisis_response()
        await save_conversation(
            site_id=site_id,
            session_id=session_id,
            user_message=request.message,
            bot_response=crisis_response,
            matched_chunk_ids=[],
            used_global_fallback=False,
            had_disclaimer=False,
            tokens_used=0,
            response_time_ms=int((time.time() - start_time) * 1000),
            flagged_keyword=flagged_keyword,
        )
        return ChatResponse(
            answer=crisis_response,
            session_id=session_id,
            crisis_detected=True,
        )

    # ── 2. Embed user question ───────────────────────────────
    query_embedding = await embed_text(request.message)

    # ── 3. Semantic search in site's knowledge base ──────────
    site_chunks = await semantic_search(site_id, query_embedding, top_k=5)
    used_global = False
    all_chunks = site_chunks

    # ── 4. Global fallback if site has no good matches ───────
    if not site_chunks and site.get("enable_global_fallback"):
        global_chunks = await global_search(query_embedding, top_k=3)
        if global_chunks:
            all_chunks = global_chunks
            used_global = True

    if not all_chunks:
        no_info_response = (
            "I don't have information about that on this website. "
            "Please contact us directly for assistance."
        )
        return ChatResponse(answer=no_info_response, session_id=session_id)

    # ── 5. Get disclaimer for sensitive sites ────────────────
    disclaimer = get_disclaimer(site_type)
    had_disclaimer = bool(disclaimer)

    # ── 6. Generate LLM answer ───────────────────────────────
    context_texts = [c["content"] for c in all_chunks]
    answer, tokens_used = await generate_answer(
        user_message=request.message,
        context_chunks=context_texts,
        site=site,
        disclaimer=disclaimer,
        conversation_history=request.conversation_history,
    )

    # Apply disclaimer prefix if not already handled by LLM prompt
    final_answer = apply_disclaimer(answer, disclaimer) if had_disclaimer else answer

    # ── 7. Save to analytics ─────────────────────────────────
    response_ms = int((time.time() - start_time) * 1000)
    await save_conversation(
        site_id=site_id,
        session_id=session_id,
        user_message=request.message,
        bot_response=final_answer,
        matched_chunk_ids=[str(c["id"]) for c in all_chunks],
        used_global_fallback=used_global,
        had_disclaimer=had_disclaimer,
        tokens_used=tokens_used,
        response_time_ms=response_ms,
    )

    return ChatResponse(
        answer=final_answer,
        session_id=session_id,
        used_fallback=used_global,
        had_disclaimer=had_disclaimer,
    )
