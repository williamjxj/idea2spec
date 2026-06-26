## Full Stack

```text
Frontend:
  Next.js 15 (App Router)
  React 19, inline styles (MVP)

Backend:
  FastAPI + Uvicorn (port 8100)

Agent Orchestration:
  LangGraph (CLI pipeline)
  Direct calls (UI agent buttons)

LLM Layer:
  OpenAI-compatible router (httpx async)
  DeepSeek, Kimi, MiniMax

Storage:
  SQLite via aiosqlite (persistent, data/projects.db)
  WAL mode

Exports:
  Markdown workspace, HTML report, Mermaid diagram

Infra:
  Local dev (MacBook)
```

## LLM Routing

| Agent | Provider | Model |
|-------|----------|-------|
| Business Analysis | Kimi | `kimi-k2.5` |
| Product Manager | DeepSeek | `deepseek-v4-pro` |
| Architect | DeepSeek | `deepseek-v4-pro` |
| Planner | MiniMax | `MiniMax-M2.5` |
| Fallback | DeepSeek | `deepseek-v4-pro` |
