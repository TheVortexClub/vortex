# Vortex — Architecture

> "Muito mais que um chatbot. Um universo de possibilidades."

Vortex runs fully on your own hardware. No third-party API keys, no telemetry, and no outbound
calls unless the user turns on web search.

## High-level view

```
                 ┌───────────────────────────── browser ─────────────────────────────┐
                 │  apps/web  (Next.js App Router · TS · Tailwind · Framer Motion)   │
                 │  server.mjs: serves the site, forwards /api and /v1 (real IP,     │
                 │  no stream timeout) → one address for every device                │
                 └───────────────┬───────────────────────────────────────────────────┘
                                 │ cookie session (short-lived JWT) · SSE streaming
                 ┌───────────────▼───────────────────────────────────────────────────┐
                 │  apps/api  (FastAPI, async)                                       │
                 │                                                                   │
                 │  /v1/*  OpenAI-compatible   /api/*  Vortex product API            │
                 │  ─────────────────────────────────────────────────────────────── │
                 │  Model gateway ── registry.yaml (models/) ── system prompts      │
                 │  Rate limiter · auth (local mode / argon2 accounts)               │
                 │  Services: chat · files/OCR · RAG · memory · tools · agents       │
                 │  Persistence: SQLAlchemy + Alembic (SQLite ▸ Postgres)            │
                 │  Vectors: sqlite-vec (Chroma optional)                            │
                 │  Jobs: APScheduler / RQ worker (automations, video, image)        │
                 └───┬──────────────┬───────────────┬─────────────────┬──────────────┘
                     │              │               │                 │
           OpenAI-compatible HTTP   │               │                 │
                     │              │               │                 │
           ┌─────────▼───────┐ ┌────▼─────┐  ┌──────▼──────┐   ┌──────▼──────────┐
           │ Ollama (default)│ │ llama.cpp│  │ vLLM (GPU)  │   │ SearXNG, ComfyUI│
           │ qwen2.5 Q4_K_M  │ │ server   │  │ optional    │   │ code sandbox …  │
           │ nomic-embed     │ │ GGUF     │  │             │   │ (later steps)   │
           └─────────────────┘ └──────────┘  └─────────────┘   └─────────────────┘
```

### Key decisions

| Concern | Choice | Why |
|---|---|---|
| Model serving | **Ollama** by default, llama.cpp server and vLLM as drop-in alternatives | All three speak the OpenAI wire format, so the API needs a single backend adapter (`openai_compat`). |
| Model identity | `models/registry.yaml` maps the public id `vortex-v0.2.1` to an upstream model + system prompt + defaults | New versions (v0.3, LoRA fine-tunes) are added by config only. Clients never see the upstream name. |
| Own API | FastAPI with `/v1/chat/completions`, `/v1/models`, `/v1/embeddings` | Any OpenAI SDK/tool works by pointing `base_url` at Vortex. No API key needed. |
| Streaming | SSE (OpenAI chunk format) + `POST /v1/chat/completions/{id}/cancel` | SSE works with every OpenAI client; cancel powers the UI "stop" button. Client disconnect also aborts upstream generation. |
| Auth | `VORTEX_LOCAL_MODE=true` (single user, no login) or accounts: argon2 passwords + short-lived JWT in an httpOnly cookie (Bearer for API clients) | One notebook can serve everyone; each user sees only their own chats. |
| Storage | SQLite (aiosqlite) by default, Postgres via `--profile postgres`; Alembic migrations | One-file install, scales up without code changes. |
| Vectors | sqlite-vec (step 5) | Same file as the main DB; Chroma optional. |
| Offline dev / CI | `VORTEX_MOCK_BACKEND=true` | Run the API and UI with no model downloaded; tests use it. |
| Privacy | Ports bound to `127.0.0.1`, `NEXT_TELEMETRY_DISABLED=1`, no analytics | Nothing leaves the machine by default. |

## Folder structure

```
vortex/
├── compose.yaml                # docker compose up → web, api, ollama (+ postgres/llamacpp profiles)
├── .env.example                # every setting, documented
├── apps/
│   ├── api/                    # FastAPI backend (Python 3.11+)
│   │   ├── vortex_api/
│   │   │   ├── main.py         # app factory, middleware, routers
│   │   │   ├── config.py       # pydantic-settings (VORTEX_* env vars)
│   │   │   ├── registry.py     # model registry loader (YAML + ${ENV:-default})
│   │   │   ├── backends/       # openai_compat (Ollama/llama.cpp/vLLM), mock
│   │   │   ├── services/       # chat payload building, streaming, usage
│   │   │   ├── routers/        # v1 (OpenAI-compatible), system (/health, /api/*)
│   │   │   ├── schemas/        # request/response models
│   │   │   ├── db.py, models_db.py
│   │   │   └── ratelimit.py
│   │   ├── migrations/         # Alembic
│   │   └── tests/              # pytest
│   └── web/                    # Next.js app (step 1: shell + API status; full UI from step 3)
├── models/
│   ├── registry.yaml           # public model ids → backend + upstream model + prompt + defaults
│   ├── prompts/                # Vortex identity / tone system prompts
│   ├── Modelfile               # optional: bake Vortex into an Ollama model
│   ├── finetune/               # LoRA/QLoRA with Unsloth or Axolotl → GGUF
│   └── gguf/                   # local GGUF weights for llama.cpp (git-ignored)
├── infra/
│   ├── docker/                 # api.Dockerfile, web.Dockerfile
│   ├── compose/gpu.yaml        # NVIDIA override + vLLM profile
│   └── ollama/pull-models.sh   # first-run model download
└── docs/                       # architecture, API reference, roadmap
```

## Planned API surface

Implemented in step 2 (✅) and planned (⏳):

| Endpoint | Status |
|---|---|
| `GET /health`, `GET /api/health` | ✅ |
| `GET /v1/models`, `GET /v1/models/{id}` | ✅ |
| `POST /v1/chat/completions` (stream + non-stream) | ✅ |
| `POST /v1/chat/completions/{id}/cancel` | ✅ |
| `POST /v1/embeddings` | ✅ |
| `GET /api/models` (UI metadata: badge, description) | ✅ |
| `GET /api/usage` (tokens, latency, tokens/s) | ✅ summary; GPU/CPU/RAM in step 4 |
| `/api/conversations`, `/api/messages` (history, chat SSE, regenerate, edit, branch, export) | ✅ step 3 |
| `/api/auth/*` (argon2 accounts, JWT cookie or Bearer) | ✅ step 3 |
| `/api/projects`, `/api/settings`, `/api/usage/history`, `/api/system`, `/api/admin/*` | ✅ step 4 |
| `/api/files` (upload, OCR, RAG), `/api/memory` | ✅ step 5 |
| `/api/tools` (status, code run), `/api/images`, `/api/jobs` | ✅ step 6 |
| `/api/agents`, `/api/automations` | ⏳ step 7 |

## Request flow: `POST /v1/chat/completions`

1. Rate limiter checks the client IP (sliding 60 s window).
2. The registry resolves `model` (id or alias, or the default) to a `ModelSpec`.
3. The payload is rewritten: upstream model name, Vortex system prompt merged in front,
   registry defaults (temperature, max_tokens…) for anything the client left out.
4. The gateway sends it to the model's backend (Ollama by default).
5. The response or each SSE chunk gets the Vortex completion id and public model id.
6. Latency, time-to-first-token, token counts and tokens/s go to `usage_events`.
