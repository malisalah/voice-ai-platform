"""Async web crawler with politeness (robots.txt, delays, rate limits)."""

import asyncio
from collections import deque
from datetime import datetime
from typing import Set
from urllib.parse import urljoin, urlparse

import httpx
from structlog import get_logger

from app.models.schemas import CrawlJobStatus
from app.utils.robots import RobotsChecker
from config import settings

logger = get_logger(__name__)


class Crawler:
    """Async web crawler with politeness features."""

    def __init__(
        self,
        max_depth: int = 1,
        max_pages: int = 100,
        delay: float = 1.0,
        timeout: int = 30,
        exclude_patterns: Set[str] | None = None,
        user_agent: str = "CrawlerService/1.0",
    ):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.delay = delay
        self.timeout = timeout
        self.exclude_patterns = exclude_patterns or set()
        self.user_agent = user_agent
        self.visited: Set[str] = set()
        self._client: httpx.AsyncClient | None = None
        self._robots_checker: RobotsChecker | None = None

    async def __aenter__(self) -> "Crawler":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
        )
        self._robots_checker = RobotsChecker(self.user_agent)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._robots_checker:
            await self._robots_checker.clear_cache()

    def _is_valid_url(self, url: str, base_domain: str) -> bool:
        """Check if URL should be crawled based on rules."""
        parsed = urlparse(url)

        # Check if URL matches exclusion patterns
        for pattern in self.exclude_patterns:
            if pattern in url:
                return False

        # Only follow http/https
        if parsed.scheme not in ("http", "https"):
            return False

        # Only follow same-domain URLs
        if base_domain not in parsed.netloc:
            return False

        return True

    async def _fetch(self, url: str) -> str | None:
        """Fetch a URL and return HTML content."""
        if not self._client:
            raise RuntimeError("Crawler not initialized. Use async context manager.")

        try:
            response = await self._client.get(url)
            if response.status_code == 200:
                return response.text
            logger.warning(
                "fetch_failed",
                url=url,
                status=response.status_code,
            )
            return None
        except httpx.RequestError as e:
            logger.error("fetch_error", url=url, error=str(e))
            return None

    async def _parse_links(self, html: str, base_url: str) -> list[str]:
        """Parse HTML and extract links using BeautifulSoup."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # Skip javascript: and mailto: links
            if href.startswith(("javascript:", "mailto:", "#")):
                continue
            # Resolve relative URLs
            absolute = urljoin(base_url, href)
            links.append(absolute)

        return links

    async def is_robots_allowed(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        if not self._robots_checker:
            return True
        return await self._robots_checker.is_allowed(url)

    async def crawl(self, start_url: str) -> dict:
        """Crawl a website starting from the given URL."""
        parsed = urlparse(start_url)
        base_domain = parsed.netloc

        self.visited = {start_url}
        to_visit = deque([(start_url, 0)])  # (url, depth)
        pages = []
        failed = 0

        async with self:
            while to_visit and len(pages) < self.max_pages:
                url, depth = to_visit.popleft()

                if depth > self.max_depth:
                    continue

                # Check robots.txt
                if not await self.is_robots_allowed(url):
                    logger.info("robots_disallowed", url=url)
                    continue

                # Rate limiting delay
                if self.visited:
                    await asyncio.sleep(self.delay)

                logger.info("crawling", url=url, depth=depth)

                html = await self._fetch(url)
                if html is None:
                    failed += 1
                    continue

                # Extract links
                links = await self._parse_links(html, url)

                for link in links:
                    if (
                        link not in self.visited
                        and self._is_valid_url(link, base_domain)
                    ):
                        self.visited.add(link)
                        to_visit.append((link, depth + 1))

                pages.append(
                    {
                        "url": url,
                        "html": html,
                        "depth": depth,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        return {
            "pages": pages,
            "stats": {
                "pages_crawled": len(pages),
                "pages_failed": failed,
                "unique_urls": len(self.visited),
            },
        }
