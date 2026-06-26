# AI Project CTO

Multi-agent workflow engine that transforms a software idea into structured project artifacts.

```text
Idea → Business Analysis → PRD → Architecture → Tasks → Workspace
```

## Stack

- **Backend:** FastAPI + LangGraph
- **Frontend:** Next.js control panel
- **LLM:** DeepSeek, Kimi, MiniMax (OpenAI-compatible APIs)
- **Storage:** In-memory (MVP)

Full stack reference (architecture, workflows, sequence diagrams): **[docs/tech-stack.md](docs/tech-stack.md)**

## Setup

### 1. Python backend

```bash
cd ai-project-cto
python -m venv venv
source venv/bin/activate
pip install -e .
cp .env.example .env   # add your API keys
```

### 2. Run API

```bash
PYTHONPATH=. uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8100
```

### 3. Next.js UI

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000

## CLI

```bash
PYTHONPATH=. python scripts/cli.py "I want to build AI Resume SaaS" --export
```

Run specific agents:

```bash
PYTHONPATH=. python scripts/cli.py "My idea" --agents business,product
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/project/create` | Create project from idea |
| GET | `/project/{id}` | Get project state |
| POST | `/agent/business/{id}` | Run Business Analyst |
| POST | `/agent/product/{id}` | Run Product Manager |
| POST | `/agent/architect/{id}` | Run Architect |
| POST | `/agent/planner/{id}` | Run Engineering Planner |
| POST | `/project/{id}/export` | Export markdown workspace |

## LLM Routing

| Agent | Provider |
|-------|----------|
| Business Analyst | Kimi |
| Product Manager | DeepSeek |
| Architect | DeepSeek |
| Planner | MiniMax |

Configure via `.env` — see `.env.example`.

## Project Structure

```text
apps/web/                 Next.js control panel
services/api/             FastAPI + in-memory store
services/agent-runtime/   LangGraph agents
services/llm-router/      Multi-provider LLM client
packages/schemas/         Pydantic Project model
packages/prompts/         Agent system prompts
projects/                 Exported markdown workspaces
```
