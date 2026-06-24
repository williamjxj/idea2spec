# AI Project CTO — Design Spec

**Date:** 2026-06-24  
**Status:** Approved and implemented (MVP v0.1)

## Overview

AI Project CTO is a multi-agent workflow engine that transforms a software idea into structured project artifacts. It is not a chatbot — agents mutate a single `Project` object through a human-in-the-loop pipeline.

```text
Idea → Business Analysis → PRD → Architecture → Tasks → Markdown Workspace
```

## Architecture

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15 App Router control panel |
| Backend | FastAPI |
| Orchestration | LangGraph (linear pipeline + single-agent runners) |
| LLM | OpenAI-compatible router → DeepSeek, Kimi, MiniMax |
| Storage | In-memory dict (MVP) |

## Data Model

Single source of truth: `Project` (Pydantic) with optional slices:

- `business_analysis` — market, competitors, monetization
- `prd` — features, user_stories, roadmap
- `architecture` — frontend, backend, database, infra
- `tasks` — epics, issues

## Agents

| Agent | Provider | Output slice |
|-------|----------|--------------|
| Business Analyst | Kimi (temp=1) | `business_analysis` |
| Product Manager | DeepSeek | `prd` |
| Architect | DeepSeek | `architecture` |
| Engineering Planner | MiniMax | `tasks` |

Each agent receives prior artifacts as JSON context. Responses are parsed as JSON with one retry on malformed output.

## API

- `POST /project/create` — create from idea
- `POST /agent/{business|product|architect|planner}/{id}` — run one agent
- `GET /project/{id}` — fetch state
- `POST /project/{id}/export` — write markdown workspace to `projects/`

## UI

Next.js control panel: create project, run agents individually, view JSON state, export workspace.

## Workspace Export

```
projects/<slug>-<id>/
  00-overview.md
  01-business.md
  02-prd.md
  03-architecture.md
  04-roadmap.md
  05-tasks.md
```

## Out of Scope (MVP)

- Ollama / local models
- PostgreSQL persistence
- Clerk auth
- GitHub repo generator
- Coding agent
- Auto-run full pipeline

## Verification

- Unit tests: export, LLM routing config
- E2E: create project → business (Kimi) → product (DeepSeek) → export verified
