# AI Project CTO

Multi-agent workflow engine that transforms a software idea into structured project artifacts.

```text
Idea → Business Analysis → PRD → Architecture → Tasks → Markdown Workspace
```

Run 4 AI agents (Business Analyst, Product Manager, Architect, Engineering Planner) against your idea — preview their output, edit it, approve it, and export a complete project workspace.

## Quick Start

```bash
# 1. Backend
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # add API keys (DeepSeek, Kimi, MiniMax)

# 2. Run API (port 8100)
PYTHONPATH=. uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8100

# 3. Frontend (port 3000)
cd apps/web && npm install && npm run dev
```

Open **http://localhost:3000**

Or use the Makefile:

```bash
make install       # full install (venv + pip + npm)
make api           # start backend (port 8100)
make web           # start frontend (port 3000)
make reset         # wipe DB + projects (see scripts/reset.sh)
```

## CLI Pipeline

Run all agents from the terminal with a single command:

```bash
PYTHONPATH=. python scripts/cli.py "I want to build AI Resume SaaS" --export
```

Run specific agents:

```bash
PYTHONPATH=. python scripts/cli.py "My idea" --agents business,product
```

The CLI also supports `make cli IDEA="..."`.

## Preview-&-Approve Workflow

The UI follows a **human-in-the-loop** flow:

1. **Create Project** — enter your idea, gets an LLM-generated title automatically
2. **Run Agents** — click individual agent buttons or **Run All** — results appear in a **preview pane**, NOT saved to DB
3. **Live Status Tracking** — each agent row shows real-time status badges:
   - ⏳ **Pending** — waiting to run
   - 🔄 **Running** — with live elapsed timer (e.g. `12s`, `1m5s`)
   - ✅ **Done** — completed successfully
   - ❌ **Failed** — error occurred
   - Each row also displays which LLM provider powers that agent (Kimi/DeepSeek/MiniMax + model name)
4. **Review & Edit** — browse structured views (Business → PRD → Architecture → Tasks) or switch to **Raw JSON** to edit directly
5. **Approve & Save** — explicit click persists all artifacts to the database
6. **Export** — download as Markdown workspace, HTML report, or Mermaid architecture diagram

> **Note:** All requests — including the SSE streaming endpoint — route through the same-origin Next.js rewrite proxy. The proxy passes SSE events through in real time without buffering.

A **Saved Projects** panel lists all persisted projects — load them back for re-review or re-export.

## Stack Overview

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI + Uvicorn (port 8100) |
| **Agent Runtime** | LangGraph (CLI pipeline) / direct calls (UI) |
| **Frontend** | Next.js 15 (port 3000, `/api/*` proxied to backend) |
| **Storage** | SQLite via `aiosqlite` — persistent at `data/projects.db` (WAL mode) |
| **LLM Router** | Async httpx → OpenAI-compatible APIs |
| **Export** | Markdown workspace + HTML report + Mermaid diagram |

Full architecture: **[docs/tech-stack.md](docs/tech-stack.md)**

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/project/create` | Create project from idea |
| GET | `/project/{id}` | Get project state |
| GET | `/projects` | List all saved projects (newest first) |
| DELETE | `/project/{id}` | Delete a project |
| POST | `/agent/{name}/{id}` | Run a single agent (`business`/`product`/`architect`/`planner`) |
| POST | `/project/{id}/save-artifacts` | Approve & persist agent artifacts |
| POST | `/project/{id}/export` | Export workspace (markdown / html / mermaid) |
| GET | `/project/{id}/export/{format}/download` | Download exported file |
| GET | `/project/{id}/run-all` | SSE stream — runs all 4 agents sequentially (native `EventSource`) |
| GET | `/health` | Health check |

## LLM Routing

| Agent | Provider | Model | Temperature |
|-------|----------|-------|-------------|
| Business Analyst | Kimi | `kimi-k2.5` | 1.0 |
| Product Manager | DeepSeek | `deepseek-v4-pro` | 0.3 |
| Architect | DeepSeek | `deepseek-v4-pro` | 0.3 |
| Engineering Planner | MiniMax | `MiniMax-M2.5` | 0.3 |
| Fallback (missing key) | DeepSeek | `deepseek-v4-pro` | 0.3 |

If a provider's API key is missing, the router falls back to DeepSeek.
JSON parse failures trigger one automatic retry with a fix prompt.

Project titles are also LLM-generated (via the fallback router) — your idea "I want to build a habit tracker" becomes "Daily Habit Tracker" automatically.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | Yes | — | DeepSeek API key |
| `KIMI_API_KEY` | Yes | — | Kimi/Moonshot API key |
| `MINIMAX_API_KEY` | Yes | — | MiniMax API key |
| `CORS_ORIGINS` | No | `http://localhost:3000,http://127.0.0.1:3000` | Allowed CORS origins |
| `DATABASE_PATH` | No | `data/projects.db` | SQLite database path |
| `BACKEND_URL` | No | `http://127.0.0.1:8100` | FastAPI backend URL for Next.js rewrites |

## Project Structure

```text
apps/web/                 Next.js 15 control panel
  components/             React components (ControlPanel, BusinessView, PRDView, …)
  lib/api.ts              TypeScript API client

services/
  api/                    FastAPI backend
    main.py               Routes, CORS, error handling
    store.py              Project CRUD (SQLite via aiosqlite)
    db.py                 Database connection manager (singleton, WAL mode)
    export.py             Markdown/HTML/Mermaid workspace export
  agent_runtime/          LangGraph agents + workflow
  llm_router/             Multi-provider LLM client (httpx + JSON extraction)

packages/
  schemas/project.py      Pydantic models — single source of truth
  prompts/agents.py       Agent system prompts

scripts/cli.py            Terminal entrypoint for full pipeline

data/                     SQLite database (gitignored)
projects/                 Exported workspaces (gitignored)
tests/                    Pytest suite (12 tests)
```

## Clean Reset

To wipe all data and start fresh:

```bash
bash scripts/reset.sh        # with confirmation prompt
bash scripts/reset.sh -f     # force reset, no prompt
make reset                   # same as -f
```

This deletes `data/projects.db` and the `projects/` directory, then restarts the backend to auto-create a fresh database.

## Clean Reset

To wipe all data and start fresh:

```bash
bash scripts/reset.sh        # with confirmation prompt
bash scripts/reset.sh -f     # force reset, no prompt
make reset                   # same as -f
```

This deletes `data/projects.db` and the `projects/` directory, then restarts the backend to auto-create a fresh database.

## Testing

```bash
make test                 # PYTHONPATH=. venv/bin/pytest tests/ -q
PYTHONPATH=. venv/bin/pytest tests/ -v     # verbose
```

Backend tests use `pytest-asyncio` with an `InMemoryStore` — no database dependency.

## Related Docs

| Document | Description |
|----------|-------------|
| [Full Tech Stack](docs/tech-stack.md) | Architecture diagrams, workflows, sequence flows |
| [Next Steps & Roadmap](docs/next-steps-and-visualization.md) | Product roadmap, visualization pipeline |
| [Preview-&-Approve Flow](docs/preview-approve-flow.md) | Human-in-the-loop design for agent output review |
| [Agent Guide](AGENTS.md) | Detailed commands, agent config, quirks for developers |
| [Design Spec](docs/superpowers/specs/2026-06-24-ai-project-cto-design.md) | Original MVP design specification |
