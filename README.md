<p align="center"><img src="assets/icon.png" width="128" alt="Vortex"></p>

# Vortex v0.2.1

**Muito mais que um chatbot. Um universo de possibilidades.**

Vortex is a personal AI that runs entirely on your own machine: its own models, its own API, its
own interface. No third-party API keys, no telemetry, no cloud.

The repository has two parts:

| Part | What it is | Where |
|---|---|---|
| **Vortex GPT** (original) | A small GPT-style transformer written and trained from scratch, with a Flask chat, terminal chat and Windows desktop app. | `vortex/`, `train.py`, `server.py`, `chat.py`, `app.py`, `web/` |
| **Vortex Platform** (new) | A self-hosted AI platform: FastAPI backend with an OpenAI-compatible API, model registry, local LLM serving, and a Next.js interface (in progress). | `apps/`, `models/`, `infra/`, `docs/`, `compose.yaml` |

The platform serves two models of its own, both labeled **PRÓPRIO**:

| Model id | What runs it | Good for |
|---|---|---|
| `vortex-v0.2.1` (default) | `vortex:0.2.1`, built locally in Ollama from open weights (Qwen 2.5 / Llama 3.2) plus the Vortex identity (`models/Modelfile`). Fine-tune it with `models/finetune`. | General chat, code, analysis; RAG, tools and agents in later steps |
| `vortex-native` | The from-scratch GPT in `vortex/`, trained by `python train.py` on your conversations in `data/` | Your fully self-made model |

See [docs/architecture.md](docs/architecture.md) for the design and the roadmap.

---

## Vortex Platform

### Requirements

| | Minimum | Recommended |
|---|---|---|
| RAM | 8 GB (3B model) | 16–32 GB (7B model) |
| Disk | 5 GB | 15 GB |
| GPU | none (CPU works) | NVIDIA 8 GB+ VRAM |
| Software | Python 3.11+ and [Ollama](https://ollama.com), or Docker | |

### Option A: your notebook is the server (Windows, no Docker)

One computer runs everything: the model, the API and the website. Everyone else just opens the
site in a browser (phone, tablet, other PCs) and creates their own account. Nobody else needs to
install anything.

```powershell
# 1. Once: build the Vortex model in Ollama (llama3.2:3b, fast on CPU)
.\scripts\create-model.ps1

# 2. Start the server
.\scripts\serve.ps1
```

`serve.ps1` prints the addresses to share, for example `http://192.168.68.57:3000`. When Windows
asks, allow Node.js on **private networks**. Each person signs up with e-mail and password and only
sees their own conversations. Use `-Local` to run just for yourself without login, and `-Rebuild`
after updating the code.

To let people outside your Wi-Fi in, put the notebook behind a tunnel such as Tailscale or
Cloudflare Tunnel (not set up by Vortex), and keep `VORTEX_ALLOW_REGISTRATION=false` once everyone
has an account.

On a 3B model a CPU-only notebook answers at about 5 tokens/s, and people's requests are queued
by Ollama. Use a 7B base (`.\scripts\create-model.ps1 -Base qwen2.5:7b-instruct-q4_K_M`) when you
have 16 GB+ RAM.

Files you attach are searched by keyword out of the box. For search by meaning (better for long
documents), download the embedding model once (about 270 MB):

```powershell
ollama pull nomic-embed-text
```

Files uploaded after that are indexed by meaning automatically.

API only (no website): `.\scripts\run-api.ps1`.

Keep it running 24/7 (Ollama, auto-start, power, firewall, fixed IP): see
[docs/servidor-24h.md](docs/servidor-24h.md) (pt-BR).

### Option B: Docker (one command)

```bash
cp .env.example .env      # server mode: VORTEX_LOCAL_MODE=false and WEB_BIND=0.0.0.0
docker compose up --build
```

On first start, `ollama-init` downloads the base model (about 5 GB) and builds `vortex:0.2.1`.
Open http://localhost:3000 (API docs at http://localhost:3000/docs).

Profiles: `--profile postgres` (Postgres instead of SQLite), `--profile llamacpp` (serve a GGUF
fine-tune), and `-f infra/compose/gpu.yaml` for NVIDIA GPUs (adds the `vllm` profile).

The API is never exposed directly: the website forwards `/api` and `/v1` to it, so there is a
single address to share.

### Using the API

No API key needed. The API follows the OpenAI request format, so existing apps and SDKs can talk to
**your** server by changing the base URL. Requests never go to OpenAI or anyone else.

In server mode, log in first and send the token you get back:

```bash
curl -X POST http://localhost:3000/api/auth/login -H "Content-Type: application/json"   -d '{"email": "voce@example.com", "password": "..."}'        # → {"access_token": "..."}
curl http://localhost:3000/v1/models -H "Authorization: Bearer <access_token>"
```

```bash
# models
curl http://localhost:8000/v1/models

# chat
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "vortex-v0.2.1", "messages": [{"role": "user", "content": "Olá, Vortex!"}]}'

# streaming (SSE). The completion id is in the X-Vortex-Completion-Id header.
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "vortex-native", "messages": [{"role": "user", "content": "oi"}], "stream": true}'

# stop a running generation
curl -X POST http://localhost:8000/v1/chat/completions/<completion-id>/cancel

# embeddings (needs: ollama pull nomic-embed-text)
curl http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" -d '{"input": "Olá mundo"}'
```

JavaScript:

```js
const res = await fetch("http://localhost:8000/v1/chat/completions", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ messages: [{ role: "user", content: "Olá!" }] }),
});
console.log((await res.json()).choices[0].message.content);
```

Other endpoints: `GET /health`, `GET /api/health` (model backend status), `GET /api/models`
(names, badges, descriptions for the UI), `GET /api/usage` (tokens, latency, tokens/s),
`/api/auth/*` (accounts), and `/api/conversations` (history: create, list/search, rename, pin,
delete, branch, export to Markdown, and `POST /api/conversations/{id}/chat` to send, regenerate or
edit with a streamed answer). Full reference at `/docs`.

### Adding a model version

Edit [models/registry.yaml](models/registry.yaml); no code changes. There's a commented example
for `vortex-v0.3`. Every value accepts `${ENV_VAR:-default}`.

### Development and tests

```bash
cd apps/api
python -m venv .venv && .venv/Scripts/activate     # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
pytest              # 129 tests; no model needed (fake backends)
ruff check .
VORTEX_MOCK_BACKEND=true uvicorn vortex_api.main:create_app --factory --reload   # simulated answers
```

Web app:

```bash
cd apps/web
npm install
npm run dev         # http://localhost:3000 (needs the API on :8000)
npm run test:e2e    # Playwright UI tests (uses installed Edge/Chrome, simulated model)
```

### Roadmap

1. ✅ Repo scaffold + docker compose (web, api, ollama, db)
2. ✅ Model serving + OpenAI-compatible `/v1` API with streaming, cancel, usage, rate limit
3. ✅ Chat interface (mockup layout, streaming, history, Ctrl+K, light/dark, mobile) + accounts
4. ✅ Projects, usage & performance dashboard, settings, server admin
5. ✅ Files (PDF, Word, Excel, CSV, code, images) with OCR, search over files (RAG), memory
6. ✅ Tools: web search (SearXNG), image generation (ComfyUI), isolated code runner — see [docs/ferramentas.md](docs/ferramentas.md)
7. Agents and automations
8. Video generation, library, explore, polish
9. v1.0

---

## Vortex GPT (from scratch)

A decoder-only transformer written in PyTorch and trained character by character on your own
conversations.

- Character-level tokenizer with special chat tokens
- Loss computed only on Vortex's replies, so it learns to answer instead of imitating you
- Data augmentation for user messages (case, accents, punctuation)
- Streaming web chat (Flask), terminal chat, and desktop app (pywebview)
- Windows builds through GitHub Actions
- Runs on CPU, CUDA or Apple Silicon (MPS)

### Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Train

```bash
python train.py
python train.py --max-steps 5000 --learning-rate 1e-3
python train.py --n-layer 6 --n-embd 256 --n-head 8
python train.py --resume --max-steps 2000
```

The model and tokenizer are saved to `checkpoints/`. The platform API picks them up automatically
as `vortex-native`.

### Chat

```bash
python server.py     # web chat at http://127.0.0.1:5000
python chat.py       # terminal
python app.py        # desktop app (pip install pywebview)
```

### Windows build

Every push to `main` runs `.github/workflows/build.yml`, which trains the model, packages Vortex
with PyInstaller and uploads `Vortex-windows-x64` as an artifact. Pushing a tag like `v1.0.0` also
publishes the zip as a GitHub release.

To build locally on Windows:

```bash
pip install pyinstaller pywebview
python train.py
pyinstaller app.py --name Vortex --windowed --icon assets/icon.ico --add-data "web;web" --add-data "assets;assets" --add-data "checkpoints;checkpoints" --collect-submodules webview
```

A `checkpoints` folder placed next to `Vortex.exe` overrides the bundled model.

### Teaching Vortex

Add `.txt` files to `data/`. Every file in that folder is used for training.

```
> what the user says
< what Vortex answers
---
> a new conversation starts after ---
< answer
```

---

## Project layout

```
apps/
  api/            FastAPI platform backend (OpenAI-compatible /v1 + /api)
  web/            Next.js interface (server.mjs: one address for site + API)
models/
  registry.yaml   model ids → backends (Ollama, llama.cpp, vLLM, native)
  Modelfile       builds vortex:0.2.1 in Ollama
  prompts/        Vortex identity and tone
  finetune/       LoRA/QLoRA (Unsloth, Axolotl) → GGUF
infra/            Dockerfiles, compose overrides, Ollama init
scripts/          Windows helpers (create-model.ps1, serve.ps1, run-api.ps1)
docs/             architecture
vortex/           from-scratch GPT (config, tokenizer, model, data, engine)
train.py          training script
server.py         Flask web chat
chat.py           terminal chat
app.py            desktop app launcher
web/              Flask chat interface
data/             training conversations
checkpoints/      trained model (git-ignored)
```

## License

MIT
