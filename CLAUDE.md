# Voice AI Agent Platform — Claude Code Context

## Project Identity
Production-grade, fully self-hosted, open-source **Voice & Chat AI Agent Platform** that lets businesses embed an AI assistant into their website. The assistant answers questions using **only the content of that specific website** (no hallucination from outside knowledge).

Architecture style: **Multi-tenant microservices monorepo**
License target: Apache 2.0 (all dependencies must be open-source compatible)

---

## Monorepo Layout

```
voice-ai-platform/
├── services/
│   ├── gateway/              # API Gateway (auth, routing, rate limiting)
│   ├── voice-service/        # LiveKit + STT (faster-whisper) + TTS (Piper)
│   ├── llm-service/          # Ollama inference + prompt construction
│   ├── knowledge-service/    # PocketFlow pipelines (ingest + retrieval)
│   ├── crawler-service/      # Web crawler + HTML parser + chunker
│   ├── tenant-service/       # Tenant CRUD, API key management
│   └── web-widget/           # Embeddable JS widget (voice + chat UI)
├── shared/
│   ├── models/               # Shared Pydantic models / DB schemas
│   ├── utils/                # Logging, auth helpers, common errors
│   └── proto/                # gRPC / protobuf definitions (if used)
├── docker/
│   ├── docker-compose.yml    # Full-stack local + production compose
│   ├── docker-compose.dev.yml
│   └── configs/              # Service-specific config files
├── docs/
│   ├── architecture.md
│   ├── api-reference.md
│   └── deployment.md
├── scripts/
│   ├── seed_tenant.sh
│   └── crawl_website.sh
├── tests/
│   ├── integration/
│   └── e2e/
├── CLAUDE.md                 # ← you are here
├── .env.example
└── README.md
```

---

## Technology Stack

### Voice & Audio
| Component | Technology |
|-----------|-----------|
| Voice sessions | LiveKit (self-hosted) |
| Speech-to-Text | faster-whisper |
| Text-to-Speech | Piper TTS |

### Intelligence
| Component | Technology |
|-----------|-----------|
| LLM inference | Ollama |
| Preferred models | Llama 3.2, Qwen2.5, Mixtral 8x7B, DeepSeek-R1 |
| Knowledge retrieval | PocketFlow (NOT a vector database) |

### Backend
| Component | Technology |
|-----------|-----------|
| Framework | Python 3.11+ / FastAPI |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Task queue | Celery + Redis broker |
| Container | Docker + Docker Compose |
| Inter-service | HTTP/REST (primary), Redis pub/sub (events) |

### Frontend Widget
| Component | Technology |
|-----------|-----------|
| Widget | Vanilla JS (zero dependencies) |
| Build | esbuild |
| Embed | `<script src="agent.js" data-tenant-id="..."></script>` |

---

## Service Contracts & Ports

| Service | Internal Port | Responsibility |
|---------|--------------|----------------|
| gateway | 8000 | Auth, routing, tenant resolution, rate limiting |
| voice-service | 8001 | LiveKit sessions, STT, TTS |
| llm-service | 8002 | Ollama wrapper, streaming, prompt building |
| knowledge-service | 8003 | PocketFlow ingestion + retrieval |
| crawler-service | 8004 | Crawl, parse, chunk, index websites |
| tenant-service | 8005 | Tenant CRUD, API key lifecycle |
| web-widget | 8006 | Serve agent.js + widget assets |
| LiveKit | 7880/7881 | WebRTC media server |
| Ollama | 11434 | LLM inference |
| PostgreSQL | 5432 | Persistent storage |
| Redis | 6379 | Cache + pub/sub + Celery broker |

---

## Data Flow

### Voice Interaction Flow
```
Browser mic
  → LiveKit WebRTC (voice-service)
  → faster-whisper STT  →  transcript text
  → knowledge-service   →  relevant context chunks (PocketFlow) using the https://github.com/The-Pocket/PocketFlow-Template-Python 
  → llm-service         →  streamed LLM response (Ollama) running in localhost (the host operating system)
  → Piper TTS           →  audio bytes
  → LiveKit             →  audio back to browser
```

### Knowledge Ingestion Flow
```
Tenant submits URL
  → crawler-service: crawl pages → clean HTML → chunk text
  → knowledge-service: run PocketFlow ingest pipeline
  → PostgreSQL: store structured chunks + metadata
  → Redis: cache hot chunks per tenant
```

### Chat Interaction Flow
```
Browser sends text message (widget)
  → gateway (auth + tenant resolution)
  → knowledge-service  →  context retrieval
  → llm-service        →  streaming response
  → gateway            →  SSE stream back to browser
```

---

## Multi-Tenancy Rules

- Every tenant has a unique `tenant_id` (UUID)
- All DB tables include `tenant_id` as partition key
- API keys are scoped per tenant — never cross-tenant access
- Knowledge bases are fully isolated per tenant
- LLM model selection is configurable per tenant (falls back to platform default)
- Rate limits are enforced per tenant at the gateway

---

## PocketFlow Usage (Critical)

**Do NOT use vector databases (no Chroma, no Pinecone, no Qdrant).**
Use PocketFlow deterministic pipelines for all retrieval.

Pipeline naming convention:
- `ingest_pipeline` — crawl → clean → chunk → store
- `retrieval_pipeline` — query → score → rank → return top-k chunks
- `context_pipeline` — retrieved chunks → format → inject into LLM prompt

Store chunked content as structured rows in PostgreSQL with:
- `tenant_id`, `url`, `chunk_index`, `content`, `metadata`, `created_at`

---

## Each Service Internal Structure

Every FastAPI service follows this structure:

```
services/<name>/
├── app/
│   ├── routers/       # FastAPI route handlers
│   ├── services/      # Business logic layer
│   ├── models/        # Pydantic request/response models
│   └── utils/         # Helpers specific to this service
├── main.py            # FastAPI app factory + router registration
├── config.py          # Pydantic Settings (reads from env)
├── requirements.txt
└── Dockerfile
```

---

## Coding Conventions

- **Python**: follow PEP8, use `ruff` for linting, `black` for formatting
- **Type hints**: mandatory on all function signatures
- **Async**: use `async def` for all route handlers and I/O-bound service methods
- **Error handling**: raise `HTTPException` at router level, use custom exceptions in service layer
- **Config**: all config via environment variables using `pydantic-settings`; no hardcoded secrets
- **Logging**: use Python `structlog` with JSON output (structured logs for production)
- **Tests**: `pytest` + `httpx.AsyncClient` for integration tests per service

---

## Environment Variables (`.env.example` pattern)

```bash
# Platform
PLATFORM_SECRET_KEY=changeme
ENVIRONMENT=development

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/voiceai

# Redis
REDIS_URL=redis://redis:6379/0

# LiveKit
LIVEKIT_URL=ws://livekit:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=devsecret

# Ollama
OLLAMA_BASE_URL=http://ollama:11434
#OLLAMA_DEFAULT_MODEL=llama3.2

OLLAMA_DEFAULT_MODEL=qwen3.5:cloud

# Structured output / tool calls
OLLAMA_CODER_MODEL=qwen3-coder-next:cloud

# Local fallback (privacy-sensitive tenants)
OLLAMA_LOCAL_FALLBACK_MODEL=gpt-oss:20b

# Embedding (nomic is fine for similarity search if you add it later)
OLLAMA_EMBED_MODEL=nomic-embed-text:latest

# Whisper
WHISPER_MODEL_SIZE=base  # tiny | base | small | medium | large-v3

# Piper TTS
PIPER_MODEL_PATH=/models/piper/en_US-lessac-medium.onnx
```

---

## Docker Compose Strategy

- `docker-compose.yml` — production-style, all services wired
- `docker-compose.dev.yml` — mounts source code as volumes for hot reload
- Services communicate on internal Docker network `voiceai-net`
- External ports only exposed for: gateway (8000), LiveKit (7880, 7881), widget (8006)
- Ollama uses GPU if available (`deploy.resources.reservations.devices`)

---

## Build & Run Commands

```bash
# Start full stack
docker compose -f docker/docker-compose.yml up --build

# Development mode (hot reload)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up

# Run all tests
pytest services/ -v

# Lint entire repo
ruff check . && black --check .

# Crawl a website for a tenant
./scripts/crawl_website.sh <tenant_id> <url>

# Create a new tenant
./scripts/seed_tenant.sh <tenant_name> <website_url>
```

---

## Phase Build Order (for Claude Code sessions)

When scaffolding from scratch, build in this order to respect dependencies:

1. `shared/` — models, utils, DB base
2. `services/tenant-service/` — tenant CRUD, API keys
3. `services/gateway/` — auth middleware, routing
4. `services/crawler-service/` — crawl + chunk
5. `services/knowledge-service/` — PocketFlow ingest + retrieval
6. `services/llm-service/` — Ollama wrapper
7. `services/voice-service/` — LiveKit + STT + TTS
8. `services/web-widget/` — JS widget build
9. `docker/docker-compose.yml` — full wiring
10. `tests/` — integration test suite

---

## Security Rules (Always Enforce)

- JWT tokens required on all non-public endpoints
- Tenant ID extracted from JWT — never from request body
- All LLM prompts must have system-level guardrail: _"Answer only using the provided context. Do not use outside knowledge."_
- Input sanitization before passing user text to LLM (strip prompt injection patterns)
- API keys hashed (bcrypt) in DB — never stored in plaintext
- Rate limiting: per-tenant, per-IP, enforced at gateway using Redis sliding window

---

## Reference Repositories

- Voice agent base: https://github.com/ShayneP/local-voice-ai
- PocketFlow template: https://github.com/The-Pocket/PocketFlow-Template-Python
