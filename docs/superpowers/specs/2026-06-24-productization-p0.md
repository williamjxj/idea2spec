# AI Project CTO — Productization P0

**Date:** 2026-06-24
**Status:** Design — pending review

## Overview

Productization Phase 0 transforms AI Project CTO from a local MVP into something that can survive a server restart and deliver a complete pipeline in one click. It also introduces the architectural foundation for diversified output (visual diagrams, multiple export formats, richer agent artifacts).

### Goals

1. **Database persistence** — projects survive server restart, enabling real usage
2. **One-click pipeline** — run all 4 agents sequentially with live progress in the UI
3. **Architecture hooks** — storage and schema designed to accommodate future rich/diversified outputs

### Non-goals (explicitly deferred)

- User authentication / multi-tenant — single-user for now
- Agent prompt upgrades — prompts stay as-is
- UI redesign — structure display upgrades are P1
- Docker deployment — P3
- Actual diversified output implementations (diagrams, PDF, etc.) — deferred to post-P0

---

## 1. Database Persistence

### 1.1 Technology choice

**PostgreSQL via asyncpg** (no ORM).

| Option | Verdict |
|--------|---------|
| SQLAlchemy async | Too heavy for 4–5 tables. Adds migration tooling complexity. |
| psycopg async | asyncpg is faster, mature, std for async Postgres in Python. |
| Supabase client | Adds network dependency to a local DB. Good option when deploying to Supabase cloud later. |

Decision: `asyncpg` for the connection pool. Schema managed by explicit DDL in `scripts/init_db.sql`, run on `lifespan` startup.

### 1.2 Schema

```sql
CREATE TABLE projects (
    id          UUID PRIMARY KEY,
    idea        TEXT NOT NULL,
    business_analysis JSONB,
    prd              JSONB,
    architecture     JSONB,
    tasks            JSONB,
    exports          JSONB DEFAULT '[]'::jsonb,  -- array of ExportArtifact
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- `business_analysis`, `prd`, `architecture`, `tasks` are nullable JSONB — mirrors the Pydantic `Optional` fields. When null, the agent hasn't run yet.
- `exports` is a JSONB array. Each element:
  ```json
  {
    "format": "markdown",
    "type": "workspace",
    "content": "...",
    "files": [{"name": "00-overview.md", "content": "..."}],
    "created_at": "2026-06-24T00:00:00Z"
  }
  ```
  This array structure is the hook for future diversified outputs: add new `format` values (`pdf`, `html`, `mermaid`, `png-diagram`) without schema changes.

### 1.3 Migration strategy

- SQL file: `scripts/init_db.sql` — idempotent `CREATE TABLE IF NOT EXISTS`
- Run on FastAPI startup via `lifespan` event: read the SQL file, execute it
- No Alembic, no migration versions. Schema additions in future phases will be additive `ALTER TABLE` statements in the same startup script.

### 1.4 asyncpg connection management

- `services/api/db.py` — singleton `asyncpg.Pool` initialized at startup
- Pool config: `min_size=2, max_size=10` (single-user MVP)
- Environment variables:
  - `DATABASE_URL` — full connection string (default: `postgresql://postgres:postgres@localhost:5432/ai_project_cto`)
  - Individual vars: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`

### 1.5 Store refactor

`services/api/store.py` becomes async:

```python
class ProjectStore:
    async def create(self, idea: str) -> Project
    async def get(self, project_id: str) -> Project | None
    async def save(self, project: Project) -> Project
    async def list_all(self) -> list[Project]
```

Internal implementation switches from `dict` to SQL queries. Project ↔ JSONB serialization uses `Project.model_dump(mode="json")` / `Project.model_validate()`.

The global `store = ProjectStore()` singleton stays — it now holds the pool reference instead of the dict.

### 1.6 Existing in-memory behavior

On startup, the `projects` table is empty (fresh DB). Projects created in a previous server session are loaded from the database. No data loss on restart.

The `projects/` exported directory continues to be gitignored and lives alongside DB persistence — export writes to disk, the project state lives in DB.

---

## 2. One-Click Pipeline (Run All)

### 2.1 Backend: SSE endpoint

**`GET /project/{id}/run-all`** — returns `text/event-stream` (native `EventSource` on the frontend).

Event sequence:

```
event: agent_start
data: {"agent": "business"}

event: agent_complete
data: {"agent": "business"}

event: agent_start
data: {"agent": "product"}

event: agent_complete
data: {"agent": "product"}

event: agent_start
data: {"agent": "architect"}

event: agent_complete
data: {"agent": "architect"}

event: agent_start
data: {"agent": "planner"}

event: agent_complete
data: {"agent": "planner"}

event: complete
data: {"project": { ... full Project JSON ... }}
```

Final `complete` event carries the full `Project` as JSON, same shape as the individual agent endpoints.

**Implementation:** Use FastAPI's `StreamingResponse` with `EventSourceResponse` pattern (manual `async for` / `async generator`). The LangGraph `workflow.py` `build_pipeline_graph` is reused — but instead of returning a single result, we wrap each node call in a yield.

Key detail: the existing `workflow.py` graph is a `StateGraph` that runs all nodes before returning. For SSE, we need to either:
- (a) Execute the graph step-by-step and yield after each node, OR
- (b) Wrap individual agent calls in a custom loop that yields, reusing the `run_single_agent()` from `agents.py`

Decision: **(b)** — simpler, reuses existing code, avoids modifying the LangGraph internals. The "run all" endpoint is a simple sequential loop:

```python
async def run_all(project_id: str):
    project = await store.get(project_id)
    for agent in ["business", "product", "architect", "planner"]:
        yield Event("agent_start", {"agent": agent})
        project = await run_single_agent(agent, project, router)
        await store.save(project)
        yield Event("agent_complete", {"agent": agent})
    yield Event("complete", {"project": project.model_dump(mode="json")})
```

The LangGraph pipeline (`workflow.py`) is kept as-is for CLI usage. The UI path uses the SSE endpoint.

### 2.2 Frontend: Progress UI

**New button:** "Run All Agents" — visually distinct (gradient/primary) above the individual agent buttons.

**Progress display:** A progress tracker below the button:

```
[Business] ✅  [Product] 🔄  [Architect] ⏳  [Planner] ⏳
```

States: ⏳ pending → 🔄 running → ✅ complete / ❌ failed.

**Implementation:** `EventSource` connects to `/api/project/{id}/run-all`. On each `agent_complete` event, update the tracker state. On `complete`, update the Project JSON display. On error, show error state and stop.

The individual agent buttons remain available for retry/re-run.

**State machine for Run All:**

| State | Meaning |
|-------|---------|
| idle | Not started |
| running | Pipeline in progress |
| complete | All agents succeeded |
| partial_failure | Some agents failed, others succeeded |

If an agent fails, the pipeline stops (fail-fast), marks the failed agent with ❌, and remaining agents stay ⏳. User can retry from the failed agent onward.

### 2.3 Error handling

- LLM failure during any agent → stores partial state (successful agents are saved) → returns error event → frontend shows failure state
- Connection drop → client-side `EventSource` `onerror` handler → show "Connection lost" message
- Timeout per agent: 120 seconds (matches existing LLM timeout)

---

## 3. Architecture Hooks for Diversified Output

### 3.1 ExportArtifact model

```python
class ExportFile(BaseModel):
    name: str        # "00-overview.md"
    content: str     # file content

class ExportArtifact(BaseModel):
    format: str      # "markdown" | "pdf" | "html" | "mermaid" | "png-diagram"
    type: str        # "workspace" | "business-report" | "architecture-diagram"
    files: list[ExportFile]
    created_at: datetime
```

### 3.2 Hook points in the codebase

| Layer | Hook | Future extension |
|-------|------|------------------|
| Schema | `Project.exports: list[ExportArtifact]` | Add new `format` values |
| Store | `exports` JSONB column | No schema change needed |
| Export | `services/api/export.py` | Add `export_project_workspace(project, format="pdf")` |
| API | `POST /project/{id}/export?format=...` | Accept format parameter |
| Agent prompts | `packages/prompts/agents.py` | In future: prompt agents to include diagram data |

### 3.3 Not implemented in P0

The `exports` field is created in the schema and populated on Markdown export (default format). No PDF/HTML/diagram generators are built. The column exists so future work adds data without migrations.

---

## 4. API Changes

### New endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/project/{id}/run-all` | Run all 4 agents, SSE stream |

### Modified endpoints

| Method | Path | Change |
|--------|------|--------|
| POST | `/project/create` | Now async, writes to DB |
| POST | `/agent/{name}/{id}` | Now async, calls `store.save()` internally |
| POST | `/project/{id}/export` | Also writes `ExportArtifact` to `project.exports` |
| GET | `/project/{id}` | Reads from DB (already JSON-serializable) |

### Removed

- `store.list_all()` → not exposed via API, only used internally

---

## 5. Frontend Changes

### New components

- `RunAllButton` — triggers `/project/{id}/run-all`, controls the state machine
- `PipelineProgress` — shows agent status row with icons

### Modified components

- `ControlPanel.tsx` — add Run All section above existing agent buttons, add `PipelineProgress`, disable buttons during pipeline

### No changes

- `lib/api.ts` — `runAgent()` stays same, `exportProject()` stays same
- `app/page.tsx`, `app/layout.tsx`, `next.config.js` — unchanged

---

## 6. Configuration & Environment

### New environment variables

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_project_cto
```

Or individual:
```
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=postgres
PGDATABASE=ai_project_cto
```

`.env.example` updated to include database connection options.

---

## 7. Dependencies

### Python (pyproject.toml)

```
asyncpg>=0.30.0
```

### System

- PostgreSQL 16+ running locally (or Docker: `docker run -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16`)
- Added to `Makefile`: `make db` — starts PostgreSQL via Docker if not running

---

## 8. Testing

| Area | Tests |
|------|-------|
| Store | `test_store.py` — create, get, save, round-trip JSONB |
| Run-all | `test_run_all.py` — SSE event sequence (mock LLM), partial failure handling |
| Export | `test_export.py` — update existing tests for async store |
| Config | `test_router_config.py` — no change needed |

**New test setup:** Tests use a test database (`ai_project_cto_test`) or in-memory fallback. The `ProjectStore` implementation is abstracted behind a protocol/interface so tests can swap in a mock store.

---

## 9. Implementation Order

| Step | Area | Description |
|------|------|-------------|
| 1 | DB | Create `scripts/init_db.sql`, `services/api/db.py`, update `store.py` |
| 2 | Config | Add `DATABASE_URL` handling, `.env.example`, `lifespan` startup |
| 3 | API | Update `/project/create`, `/project/{id}`, `/agent/{name}/{id}` to async store |
| 4 | Export | Update export to write `ExportArtifact` to `project.exports` |
| 5 | SSE | Create `/project/{id}/run-all` endpoint with SSE streaming |
| 6 | Frontend | Add `RunAllButton` + `PipelineProgress` components |
| 7 | Testing | Write store tests, update existing tests |
| 8 | Makefile | Add `make db` target for local PostgreSQL |

---

## 10. Open Questions (Resolved)

| Question | Decision |
|----------|----------|
| ORM vs raw SQL? | asyncpg, raw SQL. Only 1 table, no need for an ORM. |
| SSE vs WebSocket? | SSE — unidirectional progress events, simpler, native browser support. |
| Fail-fast or continue on agent failure? | Fail-fast. Save partial state so user can retry from failure point. |
| Migration tool? | No tool. Single idempotent `init_db.sql` run on startup. Future migrations are additive `ALTER TABLE`. |

---

*This spec is ready for review.*
