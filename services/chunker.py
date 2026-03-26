"""
Content Chunker
Splits HTML/text content into overlapping word chunks for embedding.
"""
import re
from bs4 import BeautifulSoup


def clean_html(html: str) -> str:
    """Strip HTML tags and clean whitespace."""
    soup = BeautifulSoup(html, "html.parser")
    # Remove script, style, nav, footer elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(
    text: str,
    chunk_size: int = 400,
    overlap: int = 50,
) -> list[str]:
    """
    Split text into overlapping word-based chunks.
    chunk_size: target words per chunk
    overlap: words to repeat between consecutive chunks
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if len(chunk.strip()) > 50:  # skip tiny chunks
            chunks.append(chunk)
        start += chunk_size - overlap
        if end == len(words):
            break

    return chunks


def prepare_chunks_from_pages(
    pages: list[dict],  # [{url, title, html_content, post_type}]
    site_id: str,
    chunk_size: int = 400,
    overlap: int = 50,
) -> list[dict]:
    """
    Process a list of pages into chunk dicts ready for DB insertion.
    Returns list of chunk records (without embeddings — added separately).
    """
    all_chunks = []
    for page in pages:
        clean = clean_html(page.get("html_content", ""))
        if not clean:
            continue
        text_chunks = chunk_text(clean, chunk_size, overlap)
        for i, chunk_text_content in enumerate(text_chunks):
            word_count = len(chunk_text_content.split())
            all_chunks.append({
                "site_id": site_id,
                "url": page.get("url", ""),
                "title": page.get("title", ""),
                "content": chunk_text_content,
                "chunk_index": i,
                "post_type": page.get("post_type", "page"),
                "token_count": word_count,  # rough estimate
                "metadata": {
                    "word_count": word_count,
                    "page_title": page.get("title", ""),
                },
            })
    return all_chunks
