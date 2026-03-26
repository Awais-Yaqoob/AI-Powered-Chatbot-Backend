"""
Playwright Scraper
Crawls WordPress sites including JS-rendered content.
Only runs during indexing — not on every chat request.
"""
import asyncio
from playwright.async_api import async_playwright, Browser, Page
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)


class WordPressScraper:
    def __init__(self, base_url: str, max_pages: int = 200):
        self.base_url = base_url.rstrip("/")
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.visited: set[str] = set()
        self.pages: list[dict] = []

    def _is_same_domain(self, url: str) -> bool:
        return urlparse(url).netloc == self.domain

    def _should_skip(self, url: str) -> bool:
        skip_extensions = (
            ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
            ".pdf", ".zip", ".mp4", ".mp3", ".css", ".js",
            "#", "mailto:", "tel:", "javascript:",
        )
        return any(url.lower().endswith(ext) or ext in url for ext in skip_extensions)

    async def _extract_page(self, page: Page, url: str) -> dict | None:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(800)  # allow JS to render

            title = await page.title()
            html_content = await page.content()

            # Extract WordPress post type from body classes if present
            body_classes = await page.evaluate(
                "() => document.body ? document.body.className : ''"
            )
            post_type = "page"
            if "single-post" in body_classes:
                post_type = "post"
            elif "single-" in body_classes:
                post_type = "custom"

            return {
                "url": url,
                "title": title,
                "html_content": html_content,
                "post_type": post_type,
            }
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
            return None

    async def _collect_links(self, page: Page, url: str) -> list[str]:
        try:
            links = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]'))
                           .map(a => a.href)
            """)
            valid = []
            for link in links:
                absolute = urljoin(url, link).split("#")[0].split("?")[0]
                if (
                    self._is_same_domain(absolute)
                    and not self._should_skip(absolute)
                    and absolute not in self.visited
                ):
                    valid.append(absolute)
            return list(set(valid))
        except Exception:
            return []

    async def scrape(self, progress_callback=None) -> list[dict]:
        """
        Full site crawl. Returns list of page dicts.
        progress_callback(pages_done, pages_found) called during crawl.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (compatible; WPChatbotIndexer/1.0; "
                    "+https://wpchatbot.ai/bot)"
                )
            )
            page = await context.new_page()

            queue = [self.base_url]
            self.visited.add(self.base_url)

            while queue and len(self.pages) < self.max_pages:
                url = queue.pop(0)
                logger.info(f"Scraping: {url}")

                page_data = await self._extract_page(page, url)
                if page_data:
                    self.pages.append(page_data)

                new_links = await self._collect_links(page, url)
                for link in new_links:
                    if link not in self.visited:
                        self.visited.add(link)
                        queue.append(link)

                if progress_callback:
                    await progress_callback(len(self.pages), len(self.visited))

                await asyncio.sleep(0.3)  # polite crawl delay

            await browser.close()

        logger.info(f"Scraping complete: {len(self.pages)} pages scraped")
        return self.pages


async def scrape_site(base_url: str, max_pages: int = 200, progress_callback=None) -> list[dict]:
    scraper = WordPressScraper(base_url, max_pages)
    return await scraper.scrape(progress_callback=progress_callback)
