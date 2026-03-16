"""HTML cleaner to remove non-content elements."""

import re
from typing import Optional

from bs4 import BeautifulSoup
from structlog import get_logger

logger = get_logger(__name__)


class HTMLCleaner:
    """Clean HTML by removing scripts, styles, nav, footers, etc."""

    # Tags to remove completely
    REMOVE_TAGS = {"script", "style", "noscript", "iframe", "svg", "canvas"}

    # CSS selectors to remove
    REMOVE_SELECTORS = {
        "nav",
        "footer",
        "header",
        ".navigation",
        ".footer",
        ".header",
        ".sidebar",
        ".ads",
        ".ad",
        ".share-buttons",
        ".social-links",
        "aside",
    }

    def __init__(self):
        self._soup_cache = {}

    def clean(self, html: str) -> str:
        """Clean HTML and extract main content.

        Removes: nav, footer, header, script, style, iframe, noscript, aside
        Keeps: main, article, p, h1-h6, li, td, th, blockquote
        """
        if not html:
            return ""

        try:
            soup = BeautifulSoup(html, "lxml")

            # Remove script and style elements
            for tag in self.REMOVE_TAGS:
                for element in soup.find_all(tag):
                    element.decompose()

            # Remove elements by CSS selectors
            for selector in self.REMOVE_SELECTORS:
                for element in soup.select(selector):
                    element.decompose()

            # Try to find main content area (keeps main, article tags)
            main_content = self._find_main_content(soup)

            if main_content:
                # Get clean text
                text = main_content.get_text(separator=" ", strip=True)
            else:
                # Fallback to body
                body = soup.find("body")
                if body:
                    text = body.get_text(separator=" ", strip=True)
                else:
                    text = soup.get_text(separator=" ", strip=True)

            # Clean up whitespace
            text = re.sub(r"\s+", " ", text).strip()

            return text

        except Exception as e:
            logger.error("html_cleaning_error", error=str(e))
            return ""

    def _find_main_content(self, soup) -> Optional[object]:
        """Try to identify the main content area.

        Prioritizes: main, article, then common class names.
        """
        # Common main content selectors - keeps main, article tags
        selectors = [
            "main",
            "[role='main']",
            "#main",
            ".main-content",
            ".content",
            "article",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element

        return None

    def extract_metadata(self, html: str) -> dict:
        """Extract metadata from HTML."""
        soup = BeautifulSoup(html, "lxml")
        metadata = {}

        # Title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)

        # Meta description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            metadata["description"] = desc_tag.get("content", "")

        # Meta keywords
        keywords_tag = soup.find("meta", attrs={"name": "keywords"})
        if keywords_tag:
            metadata["keywords"] = keywords_tag.get("content", "")

        # Open Graph tags
        og_tags = soup.find_all("meta", attrs={"property": lambda x: x and x.startswith("og:")})
        for tag in og_tags:
            prop = tag.get("property", "")
            content = tag.get("content", "")
            if prop and content:
                metadata[prop] = content

        return metadata
