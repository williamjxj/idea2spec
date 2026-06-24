## Full Stack

```text
Frontend:
  Next.js (App Router)
  Clerk (Auth - planned)

Backend:
  FastAPI

Agent Orchestration:
  LangGraph

LLM Layer:
  OpenAI-compatible router

Local Models:
  Ollama (Qwen / DeepSeek / Kimi)

Storage:
  In-memory (MVP only)

Infra:
  Local MacBook + Docker (later)
```

## LLM Strategy (Cost Optimized)

| Task Type         | Model         |
| ----------------- | ------------- |
| Business Analysis | Qwen (Ollama) |
| Product Reasoning | DeepSeek      |
| Architecture      | DeepSeek      |
| General fallback  | Ollama        |
