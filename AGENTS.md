# AI Project CTO — Agent Guide

## Project

Multi-agent workflow engine: `Idea → Business Analysis → PRD → Architecture → Tasks → Workspace`.
Python backend (FastAPI + LangGraph), Next.js 15 frontend, cloud LLMs via OpenAI-compatible router.

## Commands

All Python commands require `PYTHONPATH=.` (or `venv/bin/python`) because the package namespace
(`services.*`, `packages.*`) is not installed as a proper wheel in dev — it relies on the repo root
being on `sys.path`.

```bash
# Install both back-end and front-end
make install                    # venv + pip install -e ".[dev]" + npm install

# Run FastAPI (port 8100)
make api                        # PYTHONPATH=. uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8100

# Run Next.js (port 3000)
make web                        # cd apps/web && npm run dev

# Run tests (backend only)
make test                       # PYTHONPATH=. venv/bin/pytest tests/ -q

# Clean reset — wipes DB + projects directory
make reset                      # bash scripts/reset.sh -f

# CLI pipeline (create → agents → export)
make cli IDEA="I want to build AI Resume SaaS"
# Or manually:
PYTHONPATH=. python scripts/cli.py "I want to build AI Resume SaaS" --export
# Selective:
PYTHONPATH=. python scripts/cli.py "My idea" --agents business,product
```

### Running without Make
```bash
# Terminal 1 — backend
source venv/bin/activate && PYTHONPATH=. uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8100

# Terminal 2 — frontend
cd apps/web && npm run dev
```

## Architecture

### Ports
| Service | Port | Note |
|---------|------|------|
| FastAPI  | **8100** | The `docs/tech-stack.md` table says 8000 — it is wrong. Actual port is 8100 everywhere else. |
| Next.js  | **3000** | Proxies `/api/*` → FastAPI via `next.config.js` rewrites. |

### Key files
```
services/api/main.py          FastAPI app — CORS, endpoints, error handling
services/api/store.py         SQLite ProjectStore (aiosqlite, persistent — data/projects.db)
services/api/export.py        Markdown workspace exporter → projects/<slug>-<id>/
services/agent_runtime/       agents.py (runners), workflow.py (LangGraph pipeline)
services/llm_router/          config.py (env → provider routing), router.py (async httpx + JSON extraction)
packages/schemas/project.py   Pydantic models — source of truth for data shape
packages/prompts/agents.py    System prompts telling each LLM to return JSON only
scripts/cli.py                Terminal entrypoint — inline sys.path hack
scripts/reset.sh              Clean reset — wipes SQLite DB and project exports
apps/web/                     Next.js (no CSS framework, inline styles only)
```

### State management
- **SQLite** (`data/projects.db`, aiosqlite, WAL mode) — persistent across restarts.
- Agents mutate slices of a shared `Project` Pydantic object (not a chat).
- UI-driven: human clicks an agent button → POST `/agent/{name}/{id}` → agent runs → output returned in **preview** (NOT auto-saved). User clicks **Approve & Save** → `POST /project/{id}/save-artifacts` persists to SQLite.
- CLI-driven: linear LangGraph pipeline runs all selected agents sequentially and saves directly.

### API endpoints
```
POST  /project/create                → { idea } → Project
GET   /project/{id}                  → Project
GET   /projects                      → list[Project] (newest first)
DELETE /project/{id}                 → { deleted, idea }
POST  /agent/{name}/{id}             → Project (preview, NOT saved)
POST  /project/{id}/save-artifacts   → Project (approve & persist)
POST  /project/{id}/export           → { path, project } (markdown|html|mermaid)
GET   /project/{id}/export/{fmt}/download  → file download
GET   /project/{id}/run-all           → SSE stream (all 4 agents, native EventSource)
GET   /health                        → { status: "ok" }
```

> **SSE note:** The SSE endpoint is a **GET** request consumed via the native `EventSource` API on the frontend. It routes through the same-origin Next.js rewrite proxy (`/api/project/{id}/run-all`). The proxy does **not** buffer streaming responses — it passes SSE events through in real time. The `NEXT_PUBLIC_SSE_URL` env var is deprecated and no longer needed.

### LLM routing
| Agent | Provider | Model (default) | Temperature |
|-------|----------|----------------|-------------|
| Business | Kimi | kimi-k2.5 | 1.0 |
| Product | DeepSeek | deepseek-v4-pro | 0.3 |
| Architect | DeepSeek | deepseek-v4-pro | 0.3 |
| Planner | MiniMax | MiniMax-M2.5 | 0.3 |
| Fallback | DeepSeek | deepseek-v4-pro | 0.3 |

If a provider's API key is missing, the router falls back to DeepSeek.
JSON parse failure triggers one automatic retry with a fix prompt.

### Required env
- `DEEPSEEK_API_KEY`, `KIMI_API_KEY`, `MINIMAX_API_KEY` — cloud LLMs
- `CORS_ORIGINS` — defaults to `http://localhost:3000,http://127.0.0.1:3000`
- `NEXT_PUBLIC_API_URL` / `BACKEND_URL` — FastAPI base URL for Next.js rewrites

## Testing

- **Backend**: `pytest` + `pytest-asyncio`, `asyncio_mode = auto` (all tests are async-safe).
- **Frontend**: No test infrastructure exists. Report this if asked to add or modify tests.
- Tests live in `tests/` — 3 files: `test_router_config.py`, `test_export.py`, `test_store.py` (12 tests total).
- Run single: `PYTHONPATH=. venv/bin/pytest tests/test_export.py -v`

## Repo conventions & quirks

- **Python 3.11+** required (not 3.12+ — built for 3.11 compatibility).
- **No formatter or linter config** — no ruff, black, isort, eslint, prettier. Do not introduce one without asking.
- **No CSS framework** — inline `React.CSSProperties` in `ControlPanel.tsx` only.
- **markdownlint** is explicitly disabled in `.vscode/settings.json` — do not activate it.
- **cli.py** uses a `sys.path.insert(0, ...)` hack — do not remove it without confirming the package install flow works.
- **LangGraph** is used only for the CLI full-pipeline (`workflow.py`). The UI calls `run_single_agent()` directly — no graph.
- **`packages/schemas/project.py`** is the single source of truth for data models. The `packages/schemas/__init__.py` re-exports everything. TypeScript types in `apps/web/lib/api.ts` mirror the Python models manually.
- **`projects/` directory** is gitignored — exported markdown workspaces are not committed.
