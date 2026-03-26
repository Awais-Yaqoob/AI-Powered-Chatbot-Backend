"""
WP AI Chatbot SaaS - FastAPI Backend
Central AI backend for multi-tenant WordPress chatbot
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from api.chat import router as chat_router
from api.indexing import router as indexing_router
from api.sites import router as sites_router
from api.analytics import router as analytics_router
from core.config import settings

app = FastAPI(
    title="WP AI Chatbot SaaS API",
    description="Central AI backend for multi-tenant WordPress chatbot",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
)

# CORS - allow WordPress sites to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to registered sites in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Route registration
app.include_router(chat_router,      prefix="/api/v1/chat",      tags=["Chat"])
app.include_router(indexing_router,  prefix="/api/v1/index",     tags=["Indexing"])
app.include_router(sites_router,     prefix="/api/v1/sites",     tags=["Sites"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
