"""
Embeddings service - wraps OpenAI text-embedding-3-small
Cost: ~$0.02 per 1M tokens (practically free)
"""
from openai import AsyncOpenAI
from core.config import settings
import asyncio

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def embed_text(text: str) -> list[float]:
    """Generate embedding for a single text string."""
    text = text.replace("\n", " ").strip()
    response = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


async def embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """
    Generate embeddings for a list of texts in batches.
    OpenAI allows up to 2048 inputs per request but we batch
    conservatively to avoid timeouts on large sites.
    """
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = [t.replace("\n", " ").strip() for t in texts[i:i + batch_size]]
        response = await client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=batch,
        )
        # Sort by index to preserve order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        all_embeddings.extend([d.embedding for d in sorted_data])
        # Small delay to avoid rate limits on large batches
        if i + batch_size < len(texts):
            await asyncio.sleep(0.1)

    return all_embeddings
