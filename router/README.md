# LLMLab LLM Router

An operator‑grade, OpenAI‑compatible router that sits in front of local and remote LLM backends (e.g. Ollama) and presents a single, stable API surface for tools, UIs, and agent frameworks.

- ✅ OpenAI‑compatible `/v1/chat/completions`
- ✅ OpenAI‑compatible `/v1/models`
- ✅ Session affinity + history
- ✅ Task‑based routing
- ✅ Health‑gated backend selection
- ✅ Redis‑backed sessions
- ✅ Prometheus‑style metrics + logs

---

## 1. Architecture overview

The router is organized into three layers:

- **API layer**
  - `api/server.py` — FastAPI app factory and ASGI entrypoint
  - `api/routes.py` — `/v1/chat/completions`, `/v1/models`, registry endpoints
  - `api/system.py` — `/v1/logs`, `/v1/health`, `/v1/metrics`, `/v1/stats`

- **Core layer**
  - `core/read_configs.py` — YAML config loader
  - `core/model_registry.py` — discovers backends/models, normalizes metadata
  - `core/session_manager.py` — Redis‑backed session metadata + history
  - `core/routing_engine.py` — task classification, model selection, backend dispatch
  - `core/task_classifier.py` — keyword/LLM‑based task classification
  - `core/backend_factory.py` — instantiates backend adapters
  - `core/backend_health.py` — health gating with TTL + backoff
  - `core/router_logger.py` — bounded in‑memory + persistent logging

- **Backend layer**
  - `backends/base.py` — abstract `BackendAdapter` interface
  - `backends/ollama_adapter.py` — Ollama HTTP adapter (`/api/chat`, `/api/tags`, `/api/show`)

---

## 2. API surface

### 2.1 Chat completions

```http
POST /v1/chat/completions
Content-Type: application/json

