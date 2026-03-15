"""Unit tests for shared module components."""

import secrets
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.models.tenants import Tenant, TenantCreate, APIKey
from shared.models.crawl import CrawlJob, CrawlStats
from shared.models.chunks import Chunk
from shared.models.base import Base, IDMixin, TimestampMixin, TenantMixin
from shared.utils.auth import create_token, decode_token, create_refresh_token, verify_token, AuthError
from shared.utils.errors import APIError, AuthenticationError, AuthorizationError, NotFoundError
from shared.utils.errors import ValidationError, ConflictError, RateLimitExceededError
from shared.utils.errors import DatabaseError, ServiceError
from shared.utils.logging import get_logger


class TestJWTAuth:
    """Tests for JWT token encoding and decoding."""

    def test_jwt_encode_decode(self):
        """Encode a payload, decode it, assert same payload returned."""
        secret_key = "test-secret-key"
        payload = {"sub": "test-tenant-id", "role": "admin"}
        token = create_token(
            subject=payload["sub"],
            additional_claims={"role": payload["role"]},
            secret_key=secret_key,
            expires_minutes=60,
        )

        decoded = decode_token(token, secret_key=secret_key)

        assert decoded["sub"] == payload["sub"]
        assert decoded["role"] == payload["role"]

    def test_invalid_jwt_raises(self):
        """Decode a bad token, assert correct custom exception raised."""
        bad_token = "invalid.token.here"

        with pytest.raises(AuthError) as exc_info:
            decode_token(bad_token, secret_key="test-secret")

        assert exc_info.value.code == "AUTH_ERROR"
        assert "Invalid token" in exc_info.value.message

    def test_expired_jwt_raises(self):
        """Decode expired token, assert expiry exception raised."""
        secret_key = "test-secret-key"
        expired_payload = {"sub": "test-tenant-id"}

        now = datetime.now(timezone.utc)
        expire = now - timedelta(minutes=1)

        import jwt
        expired_token = jwt.encode(
            {**expired_payload, "exp": expire, "iat": now - timedelta(minutes=61)},
            secret_key,
            algorithm="HS256",
        )

        with pytest.raises(AuthError) as exc_info:
            decode_token(expired_token, secret_key=secret_key)

        assert exc_info.value.code == "AUTH_ERROR"
        assert "expired" in exc_info.value.message.lower()


class TestLogging:
    """Tests for structured logging."""

    def test_logger_returns_bound_logger(self):
        """Call get_logger(), assert it returns a bound structlog logger."""
        logger = get_logger("test_logger")

        assert logger is not None
        assert hasattr(logger, "bind")
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_custom_exceptions_inherit_base(self):
        """Assert all custom exceptions inherit from a base AppException."""
        exceptions_to_test = [
            APIError,
            AuthenticationError,
            AuthorizationError,
            NotFoundError,
            ValidationError,
            ConflictError,
            RateLimitExceededError,
            DatabaseError,
            ServiceError,
        ]

        for exc_class in exceptions_to_test:
            assert issubclass(exc_class, APIError)

    def test_api_error_has_required_attributes(self):
        """Assert APIError has message, status_code, code, and details."""
        error = APIError(
            message="Test error",
            status_code=400,
            code="TEST_ERROR",
            details={"field": "test"},
        )

        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.code == "TEST_ERROR"
        assert error.details == {"field": "test"}

    def test_not_found_error_includes_identifier(self):
        """Assert NotFoundError properly formats message with identifier."""
        error = NotFoundError(resource="user", identifier="123")

        assert "user" in error.message
        assert "123" in error.message
        assert error.status_code == 404

    def test_validation_error_includes_field_info(self):
        """Assert ValidationError properly handles field info."""
        error = ValidationError(message="Field required", field="email")

        assert error.details["field"] == "email"


class TestTenantModel:
    """Tests for Tenant SQLAlchemy model."""

    def test_tenant_model_fields(self):
        """Assert Tenant model has id, name, website_url, api_key_hash, created_at."""
        tenant = Tenant(
            id="test-id",
            tenant_id="tenant-123",
            name="Test Tenant",
            website_url="https://example.com",
            api_key_hash="$2b$12$testhashedkey",
        )

        assert tenant.id == "test-id"
        assert tenant.tenant_id == "tenant-123"
        assert tenant.name == "Test Tenant"
        assert tenant.website_url == "https://example.com"
        assert tenant.api_key_hash == "$2b$12$testhashedkey"
        assert hasattr(tenant, "created_at")
        assert hasattr(tenant, "updated_at")


class TestChunkModel:
    """Tests for Chunk SQLAlchemy model."""

    def test_chunk_model_fields(self):
        """Assert Chunk model has tenant_id, content, chunk_index, url."""
        chunk = Chunk(
            id="chunk-123",
            tenant_id="tenant-123",
            url="https://example.com/page",
            chunk_index=0,
            content="This is a test chunk of text.",
            metadata={"source": "test"},
        )

        assert chunk.tenant_id == "tenant-123"
        assert chunk.content == "This is a test chunk of text."
        assert chunk.chunk_index == 0
        assert chunk.url == "https://example.com/page"
        assert chunk.metadata == {"source": "test"}

    def test_chunk_model_has_timestamps(self):
        """Assert Chunk model has created_at and updated_at timestamps."""
        chunk = Chunk(
            id="chunk-456",
            tenant_id="tenant-123",
            url="https://example.com/page2",
            chunk_index=1,
            content="Another chunk.",
        )

        assert hasattr(chunk, "created_at")
        assert hasattr(chunk, "updated_at")

    def test_chunk_model_has_embedding_hash(self):
        """Assert Chunk model can optionally have embedding_hash."""
        chunk = Chunk(
            id="chunk-789",
            tenant_id="tenant-123",
            url="https://example.com/page3",
            chunk_index=2,
            content="Chunk with embedding.",
            embedding_hash="abc123embeddinghash",
        )

        assert chunk.embedding_hash == "abc123embeddinghash"


class TestCrawlModel:
    """Tests for CrawlJob model."""

    def test_crawl_job_fields(self):
        """Assert CrawlJob model has required fields."""
        job = CrawlJob(
            id="job-123",
            tenant_id="tenant-123",
            url="https://example.com",
            status="pending",
            pages_crawled=5,
            chunks_created=50,
        )

        assert job.tenant_id == "tenant-123"
        assert job.url == "https://example.com"
        assert job.status == "pending"
        assert job.pages_crawled == 5
        assert job.chunks_created == 50

    def test_crawl_stats_model(self):
        """Assert CrawlStats model has correct fields."""
        stats = CrawlStats(
            pages_crawled=10,
            pages_failed=2,
            chunks_created=100,
            total_size_bytes=50000,
        )

        assert stats.pages_crawled == 10
        assert stats.pages_failed == 2
        assert stats.chunks_created == 100
        assert stats.total_size_bytes == 50000
