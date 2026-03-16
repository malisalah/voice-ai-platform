"""URL utilities for normalization, deduplication, and filtering."""

from urllib.parse import parse_qs, urldefrag, urlparse


class URLManager:
    """Manage URL normalization, deduplication, and filtering."""

    def __init__(self, base_domain: str, exclude_patterns: list[str] | None = None):
        self.base_domain = base_domain
        self.exclude_patterns = exclude_patterns or []
        self.visited: set[str] = set()
        self.to_visit: list[str] = []

    def normalize(self, url: str) -> str:
        """Normalize URL: remove trailing slashes, fragments, and parameters."""
        if not url:
            return ""

        # Remove fragment
        url_without_fragment, _ = urldefrag(url)

        # Parse URL
        parsed = urlparse(url_without_fragment)

        # Remove query parameters
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        # Remove trailing slash (except for root)
        if normalized != "" and normalized.endswith("/") and len(normalized) > 1:
            normalized = normalized.rstrip("/")

        return normalized

    def is_valid(self, url: str) -> bool:
        """Check if URL should be crawled based on rules."""
        if not url:
            return False

        normalized = self.normalize(url)

        # Skip if already visited
        if normalized in self.visited:
            return False

        # Check exclusion patterns
        for pattern in self.exclude_patterns:
            if pattern in normalized:
                return False

        # Only follow http/https
        parsed = urlparse(normalized)
        if parsed.scheme not in ("http", "https"):
            return False

        # Only follow same-domain URLs
        if self.base_domain not in parsed.netloc:
            return False

        return True

    def add_url(self, url: str) -> bool:
        """Add URL to queue if valid. Returns True if added."""
        normalized = self.normalize(url)
        if self.is_valid(normalized):
            self.visited.add(normalized)
            self.to_visit.append(normalized)
            return True
        return False

    def add_urls(self, urls: list[str]) -> int:
        """Add multiple URLs. Returns count of URLs added."""
        count = 0
        for url in urls:
            if self.add_url(url):
                count += 1
        return count

    def get_next_url(self) -> str | None:
        """Get next URL from queue."""
        if self.to_visit:
            return self.to_visit.pop(0)
        return None

    def has_more_urls(self) -> bool:
        """Check if there are more URLs to visit."""
        return len(self.to_visit) > 0

    def get_visited_count(self) -> int:
        """Get count of visited URLs."""
        return len(self.visited)

    def clear(self) -> None:
        """Clear all visited and to_visit."""
        self.visited.clear()
        self.to_visit.clear()


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract all links from HTML using BeautifulSoup."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    links = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Skip javascript: and mailto: links
        if href.startswith(("javascript:", "mailto:", "#")):
            continue
        links.append(href)

    return links
