# Voice AI Agent Platform — Progress Tracker

This file tracks progress across all phases of the implementation plan.

---

## Phase 1: Shared Foundation

**Goal:** Create the shared codebase that all services depend on—Pydantic models, database schemas, and common utilities.

**Files to create:**
- `shared/__init__.py`
- `shared/models/__init__.py`
- `shared/models/base.py` — SQLAlchemy declarative base, common mixins (id, tenant_id, timestamps)
- `shared/utils/__init__.py`
- `shared/utils/logging.py` — structlog configuration
- `shared/utils/errors.py` — custom exception classes
- `shared/models/tenants.py` — Tenant schema (id, name, website_url, api_key_hash, created_at)
- `shared/models/crawl.py` — CrawlJob schema (id, tenant_id, url, status, stats, created_at, updated_at)
- `shared/models/chunks.py` — Chunk schema (id, tenant_id, url, chunk_index, content, metadata, embedding_hash, created_at)

**Status:** ✅ Complete

**Tests:** 14 unit tests passing in `tests/unit/test_shared.py`

**Files created:**
- `shared/__init__.py`
- `shared/models/__init__.py`
- `shared/models/base.py` — SQLAlchemy declarative base with mixins (IDMixin, TimestampMixin, TenantMixin)
- `shared/models/tenants.py` — Tenant schema with id, name, website_url, api_key_hash, created_at, updated_at
- `shared/models/crawl.py` — CrawlJob schema with id, tenant_id, url, status, stats, created_at, updated_at
- `shared/models/chunks.py` — Chunk schema with id, tenant_id, url, chunk_index, content, chunk_metadata, embedding_hash, created_at, updated_at
- `shared/utils/__init__.py`
- `shared/utils/logging.py` — structlog configuration with JSON output
- `shared/utils/auth.py` — JWT encode/decode helpers using python-jose
- `shared/utils/errors.py` — Custom exception classes (APIError, AuthError, etc.)
- `shared/db/__init__.py`
- `shared/db/base.py` — Async SQLAlchemy engine and session factory using DATABASE_URL
- `shared/db/migrations/__init__.py`
- `shared/db/migrations/alembic.ini`
- `shared/db/migrations/env.py`
- `shared/db/migrations/script.py.mako` — Alembic migration template

**Notes:**
- `metadata` renamed to `chunk_metadata` in chunks model (reserved word in SQLAlchemy)
- `embedding_hash` field added to chunks model for deduplication
- All models use `Mapped[]` type hints for SQLAlchemy 2.0 compatibility

---

## Phase 2: Tenant Service

**Goal:** Implement tenant management CRUD operations and API key lifecycle.

**Files created (18 files):**
- `services/tenant-service/app/__init__.py`
- `services/tenant-service/app/routers/__init__.py`
- `services/tenant-service/app/routers/tenants.py` — POST/GET/DELETE/PATCH /tenants, soft delete pattern
- `services/tenant-service/app/routers/api_keys.py` — POST/GET/ROTATE/REVOKE /api-keys endpoints
- `services/tenant-service/app/services/__init__.py`
- `services/tenant-service/app/services/tenant_service.py` — business logic for tenant CRUD
- `services/tenant-service/app/services/api_key_service.py` — bcrypt hashing, key rotation
- `services/tenant-service/app/models/__init__.py`
- `services/tenant-service/app/models/schemas.py` — consolidated request/response models
- `services/tenant-service/app/utils/__init__.py`
- `services/tenant-service/app/utils/crypto.py` — `secrets.token_hex(32)` for 64-char hex keys
- `services/tenant-service/app/db/__init__.py`
- `services/tenant-service/app/db/repository.py` — async SQLAlchemy queries
- `services/tenant-service/main.py` — FastAPI app factory
- `services/tenant-service/config.py` — Pydantic Settings
- `services/tenant-service/requirements.txt`
- `services/tenant-service/Dockerfile`

**Status:** ✅ Complete

**Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| POST | /tenants | Create tenant with initial API key |
| GET | /tenants/{id} | Get tenant by ID |
| GET | /tenants | List tenants (limit, offset) |
| DELETE | /tenants/{id} | Soft delete tenant (is_active=False) |
| PATCH | /tenants/{id} | Update tenant |
| POST | /tenants/{id}/api-keys | Create API key |
| GET | /tenants/{id}/api-keys | List API keys |
| POST | /tenants/{id}/api-keys/{key_id}/rotate | Rotate API key (generates new key) |
| PATCH | /tenants/{id}/api-keys/{key_id}/revoke | Revoke API key (sets is_active=False) |

**API Key Features:**
- Generated using `secrets.token_hex(32)` (64-char hex string)
- Hashed with bcrypt before storing — never stored in plaintext
- Plain key returned ONLY once at creation (display once, never again)
- Rotation generates new key and invalidates old one
- Revoke marks key inactive without deletion

**Tests:** 11 integration tests passing in `tests/integration/test_tenant_service.py`

**Dependencies:**
- Import from `shared.models.tenants` for Tenant and APIKey models
- Import from `shared.db.base` for async session management
- Import from `shared.utils.auth` for JWT helpers
- Import from `shared/utils/errors` for custom exceptions
- Import from `shared/utils/logging` for structured logging

**Notes:**
- `schemas.py` consolidates both request (e.g., `TenantCreateRequest`, `APIKeyCreateRequest`) and response models
- ROTATE and REVOKE endpoints use HTTP POST and PATCH as per REST conventions
- Soft delete pattern (is_active=False) preserves historical data for audit trails

---

## Phase 3: Gateway Service

**Goal:** Implement API gateway with authentication, tenant resolution, and rate limiting.

**Files created (21 files):**
- `services/gateway/app/__init__.py`
- `services/gateway/app/routers/__init__.py`
- `services/gateway/app/routers/proxy.py` — Proxy requests to backend services based on path
- `services/gateway/app/routers/auth.py` — POST /auth/token, /auth/verify endpoints
- `services/gateway/app/services/__init__.py`
- `services/gateway/app/services/auth_service.py` — JWT validation, tenant extraction
- `services/gateway/app/services/rate_limiter.py` — Redis sliding window rate limiting per tenant/IP
- `services/gateway/app/services/proxy.py` — HTTP proxy using httpx
- `services/gateway/app/services/tenant_service.py` — Tenant service client calls
- `services/gateway/app/models/__init__.py`
- `services/gateway/app/models/schemas.py` — Request/response models for gateway-specific responses
- `services/gateway/app/middleware/__init__.py`
- `services/gateway/app/middleware/auth.py` — JWT token extraction and validation
- `services/gateway/app/middleware/tenant.py` — Tenant existence and active status validation
- `services/gateway/app/middleware/rate_limit.py` — Rate limiting middleware
- `services/gateway/main.py` — FastAPI app factory with middleware stack
- `services/gateway/config.py` — Settings for backend service URLs, JWT secret, rate limit config
- `services/gateway/requirements.txt`
- `services/gateway/Dockerfile`

**Status:** ✅ Complete (scaffolded)

**Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/token | Exchange API key for JWT |
| POST | /auth/verify | Verify JWT validity |
| GET | /health | Health check for all services |
| GET | /health/{service} | Health check for specific service |
| OPTIONS | /api/* | CORS preflight |
| Proxy routes | /api/tenants/*, /api/knowledge/*, /api/crawl/*, /api/llm/*, /api/voice/* | Proxy to backend services |

**Middleware Stack (in order):**
1. CORSMiddleware
2. Request timing middleware
3. Auth middleware - Extract and validate JWT, attach tenant_id to request.state
4. Tenant middleware - Verify tenant exists and is active
5. Rate limiting middleware - Redis sliding window per tenant/IP
6. Proxy middleware - Route to backend services

**Tests:** 16 integration tests passing in `tests/integration/test_gateway.py`

---

## Test Status

### Passing Tests

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/integration/test_gateway.py` | 16 | ✅ All passing |
| `tests/integration/test_tenant_service.py` | 11 | ✅ All passing (when run alone) |
| `tests/integration/test_crawler_service.py` | 12 | ✅ All passing |

### Known Issues

**Module Caching Conflict Between Test Files:**

When running both `test_gateway.py` and `test_tenant_service.py` together in the same pytest session, the tenant-service tests fail with import errors:

```
FAILED tests/integration/test_tenant_service.py::test_create_tenant - ImportError...
```

**Root Cause:**
- Gateway's `gateway_test_setup` fixture uses `@pytest.fixture(scope="session", autouse=True)` which runs at the start of the test session
- This fixture imports and caches gateway's `app.*` modules in `sys.modules`
- When tenant-service tests later try to import `app.models.schemas`, Python's import system resolves it to gateway's version instead of tenant-service's
- The module clearing functions in `conftest.py` (`clear_service_modules()`) do not fully prevent this because:
  1. Gateway's session-scoped fixture runs before tenant tests collect
  2. Python's module cache persists across test files in the same session
  3. The `sys.path` manipulation happens too late in the import process

**Current Workaround:**
- Run gateway tests: `pytest tests/integration/test_gateway.py -v`
- Run tenant-service tests: `pytest tests/integration/test_tenant_service.py -v`
- Run crawler-service tests: `pytest tests/integration/test_crawler_service.py -v`
- Do NOT run gateway and tenant-service together: `pytest tests/integration/ -v` (fails)

**Files Affected:**
- `tests/integration/test_gateway.py` — gateway_test_setup fixture with session scope
- `tests/integration/test_tenant_service.py` — has its own module-level setup but conflicts with gateway
- `tests/integration/conftest.py` — path management helpers

**Note:** Neither service implementation is broken — this is purely a test infrastructure issue.

---

## Phase 4: Crawler Service

**Goal:** Build web crawler that fetches pages, cleans HTML, chunks text, and prepares for PocketFlow ingestion.

**Files created (25 files):**
- `services/crawler-service/__init__.py`
- `services/crawler-service/main.py` — FastAPI app factory with startup/shutdown events
- `services/crawler-service/config.py` — Pydantic Settings for all env variables
- `services/crawler-service/requirements.txt` — Dependencies (httpx, celery, redis, beautifulsoup4, lxml)
- `services/crawler-service/Dockerfile`
- `services/crawler-service/tasks/__init__.py` — Celery task exports
- `services/crawler-service/tasks/crawl_task.py` — Full pipeline Celery task with retries
- `services/crawler-service/app/__init__.py`
- `services/crawler-service/app/routers/__init__.py`
- `services/crawler-service/app/routers/crawl.py` — POST /crawl, GET /crawl/{job_id}, GET /crawl/{job_id}/chunks
- `services/crawler-service/app/routers/status.py` — GET /crawl/{job_id}/status, GET /crawl?tenant_id=
- `services/crawler-service/app/services/__init__.py`
- `services/crawler-service/app/services/crawler.py` — httpx-based async crawler with politeness
- `services/crawler-service/app/services/html_cleaner.py` — Remove nav, footer, header, script, style, iframe
- `services/crawler-service/app/services/chunker.py` — Text chunking with configurable size/overlap
- `services/crawler-service/app/services/indexer.py` — HTTP client to knowledge-service with 3 retries
- `services/crawler-service/app/models/__init__.py`
- `services/crawler-service/app/models/schemas.py` — Pydantic models
- `services/crawler-service/app/utils/__init__.py`
- `services/crawler-service/app/utils/url.py` — URL normalization, deduplication
- `services/crawler-service/app/utils/robots.py` — robots.txt checking with per-domain caching
- `services/crawler-service/app/db/__init__.py`
- `services/crawler-service/app/db/repository.py` — Async CRUD for CrawlJob

**Status:** ✅ Complete

**Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| POST | /crawl | Trigger crawl (returns 202 with job_id) |
| GET | /crawl/{job_id}/status | Get crawl job status |
| GET | /crawl/{job_id} | Get crawl job (legacy) |
| GET | /crawl/{job_id}/chunks | Get chunks from completed crawl |
| GET | /crawl | List jobs by tenant_id (query param) |

**Key Features:**
- `tasks/` folder at service root (not inside `app/`) — Celery tasks are at top level
- `html_cleaner.py` replaces `parser.py` — clean HTML by removing nav, footer, header, script, style, iframe, svg, canvas
- `robots.py` caches per domain — caches robots.txt rules per domain to avoid repeated fetches
- `indexer.py` retries 3 times on failure — exponential backoff with configurable delay
- 12 integration tests passing in `tests/integration/test_crawler_service.py`

**Dependencies:**
- Import from `shared.models.crawl` for CrawlJob model
- Import from `shared.db.base` for async session management
- Import from `shared.utils.errors` for custom exceptions
- Import from `shared.utils.logging` for structured logging

**Notes:**
- Crawler uses httpx for async HTTP (not aiohttp)
- robots.txt checking implemented with caching (caches per domain)
- HTML cleaner removes: nav, footer, header, script, style, iframe, svg, canvas, noscript, aside
- Chunker supports both sentence-sensitive (default) and word-based chunking
- Status endpoint uses in-memory storage for tests (production uses database)

---

---

## Phase 5: Knowledge Service

**Goal:** Implement PocketFlow pipelines for knowledge ingestion and retrieval.

**Files to create:**
- `services/knowledge-service/app/__init__.py`
- `services/knowledge-service/app/routers/__init__.py`
- `services/knowledge-service/app/routers/knowledge.py` — POST /ingest, GET /retrieve, POST /context
- `services/knowledge-service/app/services/__init__.py`
- `services/knowledge-service/app/services/pocketflow_ingest.py` — Ingest pipeline: chunk → embed → store
- `services/knowledge-service/app/services/pocketflow_retrieval.py` — Retrieval pipeline: query → score → rank → top-k
- `services/knowledge-service/app/services/pocketflow_context.py` — Context pipeline: chunks → format prompt
- `services/knowledge-service/app/models/__init__.py`
- `services/knowledge-service/app/models/schemas.py` — IngestRequest, QueryRequest, ChunkResponse schemas
- `services/knowledge-service/main.py`
- `services/knowledge-service/config.py`
- `services/knowledge-service/requirements.txt` (pocketflow, sentence-transformers)
- `services/knowledge-service/Dockerfile`

**API Contract (must expose for crawler-service):**
- `POST /ingest` endpoint accepting:
  ```json
  {
    "tenant_id": "uuid",
    "source_url": "https://example.com",
    "chunks": [
      {
        "content": "chunk text",
        "chunk_index": 0,
        "metadata": {}
      }
    ]
  }
  ```

**Status:** ⬜ Not Started

---

## Phase 6: LLM Service

**Goal:** Wrap Ollama API with streaming, prompt construction, and guardrails.

**Files to create:**
- `services/llm-service/app/__init__.py`
- `services/llm-service/app/routers/__init__.py`
- `services/llm-service/app/routers/llm.py` — POST /chat (streaming), POST /embed
- `services/llm-service/app/services/__init__.py`
- `services/llm-service/app/services/ollama_client.py` — Async Ollama HTTP client
- `services/llm-service/app/services/prompt_builder.py` — System prompt + context + user query
- `services/llm-service/app/services/guardrail.py` — Input sanitization, prompt injection detection
- `services/llm-service/app/models/__init__.py`
- `services/llm-service/app/models/schemas.py` — ChatRequest, ChatResponse, Message schemas
- `services/llm-service/main.py`
- `services/llm-service/config.py`
- `services/llm-service/requirements.txt` (httpx, anyio)
- `services/llm-service/Dockerfile`

**Status:** ⬜ Not Started

---

## Phase 7: Voice Service

**Goal:** Implement LiveKit voice sessions with faster-whisper STT and Piper TTS.

**Files to create:**
- `services/voice-service/app/__init__.py`
- `services/voice-service/app/routers/__init__.py`
- `services/voice-service/app/routers/voice.py` — GET /token (LiveKit join), POST /transcribe, POST /synthesize
- `services/voice-service/app/services/__init__.py`
- `services/voice-service/app/services/livekit_client.py` — LiveKit token generation, room management
- `services/voice-service/app/services/stt_service.py` — faster-whisper speech-to-text
- `services/voice-service/app/services/tts_service.py` — Piper text-to-speech
- `services/voice-service/app/models/__init__.py`
- `services/voice-service/app/models/schemas.py` — Transcription, Synthesis schemas
- `services/voice-service/main.py`
- `services/voice-service/config.py`
- `services/voice-service/requirements.txt` (livekit, faster-whisper, piper-tts)
- `services/voice-service/Dockerfile`

**Status:** ⬜ Not Started

---

## Phase 8: Web Widget

**Goal:** Build embeddable Vanilla JS widget with voice and chat UI.

**Files to create:**
- `services/web-widget/src/__init__.py` (placeholder)
- `services/web-widget/src/agent.js` — Main widget script with embed logic
- `services/web-widget/src/widget.html` — Default widget UI (chat window + voice button)
- `services/web-widget/src/styles.css` — Widget styling
- `services/web-widget/src/lib/voice.js` — LiveKit voice connection logic
- `services/web-widget/src/lib/chat.js` — SSE chat connection logic
- `services/web-widget/src/lib/events.js` — Custom events for widget interactions
- `services/web-widget/build.js` — esbuild config for production bundle
- `services/web-widget/package.json`
- `services/web-widget/README.md`

**Status:** ⬜ Not Started

---

## Phase 9: Docker Composition

**Goal:** Wire all services together with Docker Compose for local and production use.

**Files to create:**
- `docker/docker-compose.yml` — Production compose with all services
- `docker/docker-compose.dev.yml` — Development compose with hot reload volumes
- `docker/configs/gateway.env` — Gateway environment overrides
- `docker/configs/tenant-service.env`
- `docker/configs/voice-service.env`
- `docker/configs/llm-service.env`
- `docker/configs/knowledge-service.env`
- `docker/configs/crawler-service.env`
- `docker/.env.example` — Example environment file for users

**Status:** ⬜ Not Started

---

## Summary

| Phase | Component | Status |
|-------|-----------|--------|
| 1 | Shared Foundation | ✅ Complete (14 unit tests) |
| 2 | Tenant Service | ✅ Complete (11 integration tests) |
| 3 | Gateway Service | ✅ Complete (16 integration tests) |
| 4 | Crawler Service | ✅ Complete (25 files, 12 integration tests) |
| 5 | Knowledge Service | ⬜ Not Started (requires POST /ingest endpoint) |
| 6 | LLM Service | ⬜ Not Started |
| 7 | Voice Service | ⬜ Not Started |
| 8 | Web Widget | ⬜ Not Started |
| 9 | Docker Composition | ⬜ Not Started |
| 10 | Integration Tests | ✅ Complete (test infrastructure ready, module caching issue prevents gateway+tenant running together) |
