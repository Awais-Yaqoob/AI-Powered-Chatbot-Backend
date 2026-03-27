"""
Core configuration - loads from environment variables
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # OpenAI
    # OPENAI_API_KEY: str
    # EMBEDDING_MODEL: str = "text-embedding-3-small"
    # PRIMARY_LLM: str = "gpt-4o-mini"
    OPENAI_API_KEY: Optional[str] = None
    PRIMARY_LLM: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Anthropic (optional premium tier)
    ANTHROPIC_API_KEY: Optional[str] = None
    PREMIUM_LLM: str = "claude-haiku-4-5-20251001"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str

    # RAG settings
    CHUNK_SIZE: int = 400          # words per chunk
    CHUNK_OVERLAP: int = 50        # word overlap between chunks
    MAX_CHUNKS_RETRIEVED: int = 5
    SIMILARITY_THRESHOLD: float = 0.70
    GLOBAL_SIMILARITY_THRESHOLD: float = 0.75

    # Safety
    CRISIS_KEYWORDS: list = [
        "suicide", "self-harm", "kill myself", "end my life",
        "overdose", "hurt myself", "want to die"
    ]

    # Disclaimers per site type
    DISCLAIMERS: dict = {
        "medical": (
            "⚠️ This chatbot provides general information only and is not a substitute "
            "for professional medical advice, diagnosis, or treatment. Always consult "
            "a qualified healthcare provider for medical concerns."
        ),
        "legal": (
            "⚠️ This chatbot provides general legal information only and does not "
            "constitute legal advice. For advice specific to your situation, please "
            "consult a licensed attorney."
        ),
        "financial": (
            "⚠️ This chatbot provides general financial information only. It is not "
            "financial advice. Please consult a qualified financial advisor before "
            "making investment decisions."
        ),
        "general": "",
    }

    CRISIS_RESPONSE: str = (
        "It sounds like you may be going through something difficult. "
        "If you're in crisis, please reach out to a crisis helpline immediately. "
        "In the US, call or text 988 (Suicide & Crisis Lifeline). "
        "In Pakistan, contact Umang helpline: 0317-4288665. "
        "You are not alone."
    )

    class Config:
        env_file = ".env"


settings = Settings()
