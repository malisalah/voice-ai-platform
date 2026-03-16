"""Integration tests for crawler-service using pytest.

Tests should be run with:
    pytest tests/integration/test_crawler_service.py -v

This test file manages its own paths and modules to avoid conflicts.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, MockTransport, Response, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

# Set environment variables BEFORE importing anything else
os.environ["SERVICE_NAME"] = "crawler-service"
os.environ["SERVICE_PORT"] = "8004"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/voiceai"
os.environ["REDIS_URL"] = "redis://nonexistent:6379/0"
os.environ["KNOWLEDGE_SERVICE_URL"] = "http://localhost:8003"
os.environ["CELERY_BROKER_URL"] = "redis://nonexistent:6379/1"
os.environ["CRAWLER_DELAY_SECONDS"] = "0.1"
os.environ["CRAWLER_MAX_PAGES"] = "10"
os.environ["CRAWLER_MAX_DEPTH"] = "2"
os.environ["CRAWLER_USER_AGENT"] = "CrawlerService/1.0"
os.environ["POCKETFLOW_CHUNK_SIZE"] = "100"
os.environ["POCKETFLOW_CHUNK_OVERLAP"] = "10"

# Paths
_CRAWLER_PATH = "/home/mali/voice-ai-platform/services/crawler_service"
_SHARED_PATH = "/home/mali/voice-ai-platform/shared"
_ROOT_PATH = "/home/mali/voice-ai-platform"


def _setup_paths():
    """Set up paths for crawler-service tests."""
    for path in [_CRAWLER_PATH, _SHARED_PATH, _ROOT_PATH]:
        if path in sys.path:
            sys.path.remove(path)

    # Add in reverse order so crawler is at position 0
    if _CRAWLER_PATH not in sys.path:
        sys.path.insert(0, _CRAWLER_PATH)
    if _SHARED_PATH not in sys.path:
        sys.path.insert(0, _SHARED_PATH)
    if _ROOT_PATH not in sys.path:
        sys.path.insert(0, _ROOT_PATH)


def _clear_crawler_modules():
    """Clear crawler-service modules from cache."""
    modules_to_clear = []
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("crawler_service") or mod_name.startswith("app."):
            modules_to_clear.append(mod_name)

    for mod_name in modules_to_clear:
        if mod_name in sys.modules:
            del sys.modules[mod_name]


# ============================================================================
# Test 1: test_crawl_job_created_with_pending_status
# ============================================================================
@pytest.mark.asyncio
async def test_crawl_job_created_with_pending_status():
    """POST /crawl returns job_id and status=pending."""
    _setup_paths()
    _clear_crawler_modules()

    from main import create_app
    from httpx import ASGITransport

    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/crawl",
            json={
                "url": "https://example.com",
                "max_depth": 1,
                "exclude_patterns": ["/admin"],
            },
        )

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    assert "Crawl job" in data["message"]
    assert "example.com" in data["message"]


# ============================================================================
# Test 2: test_crawl_status_endpoint_returns_job
# ============================================================================
@pytest.mark.asyncio
async def test_crawl_status_endpoint_returns_job():
    """GET /crawl/{job_id}/status returns job data."""
    _setup_paths()
    _clear_crawler_modules()

    from main import create_app
    from httpx import ASGITransport
    from unittest.mock import patch, AsyncMock
    import app.routers.crawl as crawl_module

    # Mock the _run_crawl function to prevent actual crawling
    original_run_crawl = crawl_module._run_crawl
    crawl_module._run_crawl = AsyncMock()

    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            "/crawl",
            json={"url": "https://example.com", "max_depth": 1},
        )

        assert create_response.status_code == 202
        job_id = create_response.json()["job_id"]

        # Now get status
        status_response = await client.get(f"/crawl/{job_id}/status")

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["url"] == "https://example.com"
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data

    # Restore original
    crawl_module._run_crawl = original_run_crawl


# ============================================================================
# Test 3: test_html_cleaner_removes_nav_footer_scripts
# ============================================================================
def test_html_cleaner_removes_nav_footer_scripts():
    """HTML cleaner removes nav, footer, script, style elements."""
    _setup_paths()
    _clear_crawler_modules()

    from app.services.html_cleaner import HTMLCleaner

    html = """
    <html>
        <head>
            <script>console.log('bad');</script>
            <style>.bad { color: red; }</style>
        </head>
        <body>
            <nav>Navigation menu</nav>
            <header>Header content</header>
            <main>
                <article>
                    <h1>Main Content</h1>
                    <p>This should be kept.</p>
                </article>
            </main>
            <footer>Footer content</footer>
            <aside>Sidebar</aside>
            <iframe src="https://example.com"></iframe>
        </body>
    </html>
    """

    cleaner = HTMLCleaner()
    result = cleaner.clean(html)

    # These should be removed
    assert "Navigation menu" not in result
    assert "Footer content" not in result
    assert "Sidebar" not in result
    assert "Header content" not in result
    assert "console.log" not in result
    assert "<script>" not in result.lower()
    assert "<style>" not in result.lower()
    assert "<iframe>" not in result.lower()

    # This should be kept
    assert "Main Content" in result
    assert "This should be kept" in result


# ============================================================================
# Test 4: test_html_cleaner_keeps_main_content
# ============================================================================
def test_html_cleaner_keeps_main_content():
    """HTML cleaner preserves main, article, p, h1-h6, li, td, th, blockquote."""
    _setup_paths()
    _clear_crawler_modules()

    from app.services.html_cleaner import HTMLCleaner

    html = """
    <html>
        <body>
            <main>
                <article>
                    <h1>Heading 1</h1>
                    <h2>Heading 2</h2>
                    <h3>Heading 3</h3>
                    <h4>Heading 4</h4>
                    <h5>Heading 5</h5>
                    <h6>Heading 6</h6>
                    <p>Paragraph text</p>
                    <ul>
                        <li>Item 1</li>
                        <li>Item 2</li>
                    </ul>
                    <table>
                        <tr>
                            <td>Cell 1</td>
                            <th>Header Cell</th>
                        </tr>
                    </table>
                    <blockquote>Quote text</blockquote>
                </article>
            </main>
            <script>removed</script>
        </body>
    </html>
    """

    cleaner = HTMLCleaner()
    result = cleaner.clean(html)

    # All these should be preserved
    assert "Heading 1" in result
    assert "Heading 2" in result
    assert "Heading 3" in result
    assert "Heading 4" in result
    assert "Heading 5" in result
    assert "Heading 6" in result
    assert "Paragraph text" in result
    assert "Item 1" in result
    assert "Item 2" in result
    assert "Cell 1" in result
    assert "Header Cell" in result
    assert "Quote text" in result
    assert "removed" not in result


# ============================================================================
# Test 5: test_chunker_respects_chunk_size
# ============================================================================
def test_chunker_respects_chunk_size():
    """Chunker splits text longer than CHUNK_SIZE correctly."""
    _setup_paths()
    _clear_crawler_modules()

    from app.services.chunker import Chunker

    # Create chunker with 100 word limit, sentence_sensitive=False for word-based splitting
    chunker = Chunker(max_words=100, sentence_sensitive=False)

    # Create text with 150 words (should split into at least 2 chunks)
    words = ["word"] * 150
    text = " ".join(words)

    chunks = chunker.chunk(text, "https://example.com/page1")

    # Should have multiple chunks
    assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"

    # Check chunk word counts - each should be <= max_words
    for chunk in chunks:
        assert chunk["word_count"] <= 100
        assert chunk["page_url"] == "https://example.com/page1"
        assert "chunk_index" in chunk
        assert "content" in chunk
        assert len(chunk["content"]) > 0


# ============================================================================
# Test 6: test_chunker_respects_overlap
# ============================================================================
def test_chunker_respects_overlap():
    """Chunker shares overlap words between consecutive chunks."""
    _setup_paths()
    _clear_crawler_modules()

    from app.services.chunker import Chunker

    # Create chunker with 50 word limit and 10 word overlap
    chunker = Chunker(max_words=50, overlap_words=10)

    # Create text that will definitely create multiple chunks
    # Use many sentences to ensure chunking happens
    sentences = []
    for i in range(20):
        sentences.append(f"This is sentence number {i} with additional words.")
    text = " ".join(sentences)

    chunks = chunker.chunk(text, "https://example.com/page1")

    # Should have multiple chunks
    assert len(chunks) >= 2

    # Check overlap - consecutive chunks should share some words
    for i in range(1, len(chunks)):
        prev_content = chunks[i - 1]["content"]
        curr_content = chunks[i]["content"]

        # Get last words from previous chunk and first words from current
        prev_words = prev_content.split()[-5:]  # Last 5 words
        curr_words = curr_content.split()[:5]   # First 5 words

        # Check for common words
        common = set(prev_words) & set(curr_words)

        # At least some overlap should exist (10 word overlap)
        assert len(common) >= 1  # At least one common word should exist


# ============================================================================
# Test 7: test_chunker_no_empty_chunks
# ============================================================================
def test_chunker_no_empty_chunks():
    """Chunker never returns empty string chunks."""
    _setup_paths()
    _clear_crawler_modules()

    from app.services.chunker import Chunker

    chunker = Chunker(max_words=100)

    # Test with empty string
    empty_chunks = chunker.chunk("", "https://example.com")
    assert empty_chunks == []

    # Test with whitespace only
    whitespace_chunks = chunker.chunk("   \n\n   ", "https://example.com")
    assert whitespace_chunks == []

    # Test with very short text
    short_chunks = chunker.chunk("Short", "https://example.com")
    assert len(short_chunks) == 1
    assert short_chunks[0]["word_count"] > 0
    assert len(short_chunks[0]["content"].strip()) > 0

    # Test with text that might create empty chunk
    complex_text = "This is a test. With multiple sentences! Some in parentheses. And more."
    complex_chunks = chunker.chunk(complex_text, "https://example.com")
    for chunk in complex_chunks:
        assert len(chunk["content"].strip()) > 0
        assert chunk["word_count"] > 0


# ============================================================================
# Test 8: test_url_normalization
# ============================================================================
def test_url_normalization():
    """URL normalization removes trailing slashes, fragments, and parameters."""
    _setup_paths()
    _clear_crawler_modules()

    from app.utils.url import URLManager

    manager = URLManager(base_domain="example.com")

    # Test trailing slash removal
    assert manager.normalize("https://example.com/path/") == "https://example.com/path"
    assert manager.normalize("https://example.com/path///") == "https://example.com/path"

    # Test fragment removal
    assert manager.normalize("https://example.com/page#section") == "https://example.com/page"
    assert manager.normalize("https://example.com/page#top") == "https://example.com/page"

    # Test query parameter removal
    assert manager.normalize("https://example.com/page?param=value") == "https://example.com/page"
    assert manager.normalize("https://example.com/page?a=1&b=2") == "https://example.com/page"

    # Test combined normalization
    assert manager.normalize("https://example.com/page?x=1#top/") == "https://example.com/page"

    # Test no normalization needed
    assert manager.normalize("https://example.com") == "https://example.com"
    assert manager.normalize("https://example.com/path") == "https://example.com/path"


# ============================================================================
# Test 9: test_url_deduplication
# ============================================================================
def test_url_deduplication():
    """URL manager returns False for already-visited URL."""
    _setup_paths()
    _clear_crawler_modules()

    from app.utils.url import URLManager

    manager = URLManager(base_domain="example.com")

    url = "https://example.com/page1"

    # First add should succeed
    assert manager.add_url(url) == True

    # Already visited returns False
    assert manager.is_valid(url) == False

    # Add another URL
    url2 = "https://example.com/page2"
    assert manager.add_url(url2) == True

    # Now page2 is visited, page1 still visited
    assert manager.is_valid(url) == False
    assert manager.is_valid(url2) == False

    # Different domain should be filtered out
    url3 = "https://other.com/page"
    assert manager.add_url(url3) == False


# ============================================================================
# Test 10: test_robots_txt_blocks_disallowed_url
# ============================================================================
@pytest.mark.asyncio
async def test_robots_txt_blocks_disallowed_url():
    """Robots checker returns False for disallowed path."""
    _setup_paths()
    _clear_crawler_modules()

    from app.utils.robots import RobotsChecker

    # Mock httpx client
    async def mock_get(url, **kwargs):
        response = Mock()
        response.status_code = 200
        response.text = """User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /
"""
        return response

    # Use patch to mock the httpx AsyncClient - need to patch where it's imported
    with patch("app.utils.robots.httpx.AsyncClient") as mock_client_class:
        mock_instance = AsyncMock()
        mock_instance.get = mock_get
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_instance

        # Use context manager to initialize _client
        async with RobotsChecker(user_agent="CrawlerService/1.0") as checker:
            # Disallowed path
            result = await checker.is_allowed("https://example.com/admin/secret")
            assert result == False, f"Expected False for disallowed path, got {result}"

            # Allowed path - use a different domain to avoid cache
            result = await checker.is_allowed("https://otherdomain.com/public/page")
            assert result == True, f"Expected True for allowed path, got {result}"


# ============================================================================
# Test 11: test_indexer_posts_correct_payload
# ============================================================================
@pytest.mark.asyncio
async def test_indexer_posts_correct_payload():
    """Indexer POSTs correct payload to knowledge-service."""
    _setup_paths()
    _clear_crawler_modules()

    from app.services.indexer import Indexer

    # Mock chunks
    chunks = [
        {"content": "First chunk", "page_url": "https://example.com/1", "chunk_index": 0},
        {"content": "Second chunk", "page_url": "https://example.com/2", "chunk_index": 1},
    ]

    # Create a mock client for the indexer
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "chunks_indexed": 2, "job_id": "test-job-id"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.aclose = AsyncMock()

    indexer = Indexer(client=mock_client)

    result = await indexer.index_chunks(
        tenant_id="test-tenant-123",
        source_url="https://example.com",
        chunks=chunks,
        client=mock_client,
    )

    # Verify the call was made
    assert mock_client.post.called

    # Get the call arguments
    call_args = mock_client.post.call_args
    assert call_args is not None

    # Verify payload
    payload = call_args[1]["json"]
    assert payload["tenant_id"] == "test-tenant-123"
    assert payload["source_url"] == "https://example.com"
    assert "chunks" in payload
    assert len(payload["chunks"]) == 2


# ============================================================================
# Test 12: test_crawl_job_status_transitions
# ============================================================================
@pytest.mark.asyncio
async def test_crawl_job_status_transitions():
    """Repository updates status: pending -> running -> complete -> failed."""
    _setup_paths()
    _clear_crawler_modules()

    from app.db.repository import CrawlJobRepository
    from shared.models.crawl import CrawlJobStatus, CrawlJob
    from shared.models.base import Base
    from uuid import uuid4

    # Use in-memory SQLite
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        pool_pre_ping=False,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    TestingSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with TestingSessionLocal() as session:
        repo = CrawlJobRepository(session)
        tenant_id = "test-tenant-" + str(asyncio.get_event_loop().time())

        # 1. Create job with pending status
        job = await repo.create_job(
            tenant_id=tenant_id,
            url="https://example.com",
            max_depth=1,
        )
        assert job.status == CrawlJobStatus.PENDING
        assert job.id is not None

        # 2. Update to running
        job = await repo.update_job_status(job.id, CrawlJobStatus.RUNNING)
        assert job.status == CrawlJobStatus.RUNNING

        # 3. Update to complete
        job = await repo.update_job_status(
            job.id,
            CrawlJobStatus.COMPLETED,
            stats={"pages_crawled": 5},
            pages_crawled=5,
            chunks_created=10,
        )
        assert job.status == CrawlJobStatus.COMPLETED
        assert job.pages_crawled == 5
        assert job.chunks_created == 10

        # 4. Create another job and update to failed
        job2 = await repo.create_job(
            tenant_id=tenant_id,
            url="https://example.com/error",
            max_depth=1,
        )
        job2 = await repo.update_job_status(
            job2.id,
            CrawlJobStatus.FAILED,
            error_message="Connection timeout",
        )
        assert job2.status == CrawlJobStatus.FAILED
        assert job2.error_message == "Connection timeout"
