"""
Safety & Disclaimer Service
- Crisis keyword detection
- Site-type disclaimer injection
- Sensitive content filtering
"""
from core.config import settings


def detect_crisis(message: str) -> str | None:
    """
    Check if user message contains crisis keywords.
    Returns the matched keyword or None.
    """
    message_lower = message.lower()
    for keyword in settings.CRISIS_KEYWORDS:
        if keyword in message_lower:
            return keyword
    return None


def get_disclaimer(site_type: str) -> str:
    """
    Return disclaimer text for site type.
    Empty string if no disclaimer needed.
    """
    return settings.DISCLAIMERS.get(site_type, "")


def apply_disclaimer(response: str, disclaimer: str) -> str:
    """Prepend disclaimer to response if applicable."""
    if disclaimer:
        return f"{disclaimer}\n\n{response}"
    return response


def get_crisis_response() -> str:
    return settings.CRISIS_RESPONSE


def is_sensitive_site(site_type: str) -> bool:
    return site_type in ("medical", "legal", "financial")
