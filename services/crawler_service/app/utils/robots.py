"""Robots.txt checker with per-domain caching."""

import asyncio
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from structlog import get_logger

logger = get_logger(__name__)


class RobotsChecker:
    """Check robots.txt permissions with caching."""

    def __init__(self, user_agent: str = "CrawlerService/1.0"):
        self.user_agent = user_agent
        self._cache: dict[str, bool] = {}
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def is_allowed(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path

        # Check cache first
        if domain in self._cache:
            return self._cache[domain]

        # Check robots.txt with path
        allowed = await self._check_robots_txt(domain, path)

        # Cache result
        self._cache[domain] = allowed
        return allowed

    async def _check_robots_txt(self, domain: str, path: str = "/") -> bool:
        """Check robots.txt for a domain and path."""
        if not self._client:
            return True  # Default to allowed if no client

        robots_url = urljoin(domain, "/robots.txt")

        try:
            response = await self._client.get(
                robots_url,
                headers={"User-Agent": self.user_agent},
                timeout=10.0,
            )

            if response.status_code != 200:
                # If robots.txt doesn't exist, allow crawling
                logger.info("robots_txt_not_found", domain=domain, status=response.status_code)
                return True

            robots_content = response.text
            return self._parse_robots_txt(robots_content, path)

        except httpx.RequestError as e:
            logger.warning("robots_txt_request_failed", domain=domain, error=str(e))
            return True  # Default to allowed on error

    def _parse_robots_txt(self, content: str, path: str = "/") -> bool:
        """Parse robots.txt content and check if user agent is allowed for path."""
        lines = content.split("\n")
        disallow_patterns: list[str] = []
        allow_patterns: list[str] = []
        user_agent_found = False

        for line in lines:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse directive
            if ":" in line:
                directive, value = line.split(":", 1)
                directive = directive.strip().lower()
                value = value.strip()

                if directive == "user-agent":
                    # Check if previous rules applied to our user agent
                    if user_agent_found:
                        break

                    if value.lower() == self.user_agent.lower() or value == "*":
                        user_agent_found = True

                    # Reset rules for new user agent
                    if value.lower() == self.user_agent.lower():
                        disallow_patterns = []
                        allow_patterns = []

                elif directive == "disallow" and user_agent_found:
                    if value:
                        disallow_patterns.append(value)

                elif directive == "allow" and user_agent_found:
                    if value:
                        allow_patterns.append(value)

        # If no rules found for our user agent, allow everything
        if not user_agent_found:
            return True

        # Check disallow patterns first - if any match, return False
        # Disallow rules take precedence over allow rules
        for pattern in disallow_patterns:
            if self._path_matches_pattern(path, pattern):
                return False

        # Check allow patterns - if any match, return True
        for pattern in allow_patterns:
            if self._path_matches_pattern(path, pattern):
                return True

        return True  # Default to allowed

    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches a robots.txt pattern."""
        # Empty pattern matches everything
        if not pattern or pattern == "/":
            return True

        # Direct path match
        if path == pattern:
            return True

        # Prefix match - pattern is a prefix of path
        # e.g., pattern "/admin/" matches path "/admin/secret"
        if pattern.endswith("/"):
            return path.startswith(pattern)

        # Pattern without trailing slash - match if path starts with pattern
        # e.g., pattern "/admin" matches path "/admin/secret" or "/admin"
        return path.startswith(pattern + "/") or path == pattern

    async def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        self._cache.clear()

    async def clear_domain_cache(self, domain: str) -> None:
        """Clear cache for a specific domain."""
        self._cache.pop(domain, None)


async def check_robots_allowed(url: str, user_agent: str = "CrawlerService/1.0") -> bool:
    """Quick check if URL is allowed by robots.txt."""
    async with RobotsChecker(user_agent) as checker:
        return await checker.is_allowed(url)
