# Preview-&-Approve Flow & DB Records Viewer

## Overview

Three bugs were reported in the agent pipeline:

| # | Problem | Root Cause | Fix |
|---|---------|------------|-----|
| 1 | WebUI/CLI stuck on "Run All" — no progress updates | LLM HTTP timeout (60 s) too short for long-running model responses | Increased timeout to **300 s** |
| 2 | Agent output saved **directly** to PostgreSQL with no human review | `_run_agent()` and `/run-all` called `store.save()` immediately after each agent | Removed auto-save; introduced explicit **"Approve & Save to Database"** step |
| 3 | No UI to view or manage existing DB records | No `GET /projects` endpoint; no frontend panel | Added list/delete endpoints + collapsible **Saved Projects** panel |
| 4 | SSE streaming blocked by Next.js proxy buffering | Next.js rewrites buffer streaming responses, so status rows never update in real time | `runAllAgents()` connects directly to backend port 8100 via `NEXT_PUBLIC_SSE_URL` env var |
| 5 | No visual status feedback during Run All | Agents ran silently — all rows stayed "Pending" until completion | Added per-agent status badges (⏳→🔄→✅/❌) with live elapsed timer + LLM provider info |

---

## Files Changed

| File | Type | Change |
|------|------|--------|
| `services/api/main.py` | Backend | Removed auto-save from agents; added 3 new endpoints |
| `services/llm_router/router.py` | Backend | HTTP timeout 60 s → 300 s |
| `apps/web/lib/api.ts` | Frontend | New types + API functions + SSE direct connection |
| `apps/web/components/ControlPanel.tsx` | Frontend | Preview bar, editable JSON, saved-projects panel, status badges/elapsed timers |
| `apps/web/env.example` | Frontend | Added `NEXT_PUBLIC_SSE_URL` env var |
| `scripts/reset.sh` | Tooling | Clean reset — wipes SQLite DB + exported workspaces |
| `Makefile` | Tooling | Added `make reset` target |

---

## Backend Changes (`services/api/main.py`)

### 1. Agent endpoints no longer save

`_run_agent()` returns the agent output without calling `store.save()`:

```python
async def _run_agent(project_id: str, agent: AgentName) -> Project:
    """Run a single agent and return the result WITHOUT saving to DB."""
    project = await _get_project_or_404(project_id)
    updated = await run_single_agent(agent, project, router)
    return updated  # <-- no store.save()
```

The same applies to the `/run-all` SSE stream — `store.save()` calls were removed from the loop.

### 2. New endpoint: `POST /project/{id}/save-artifacts`

Persists artifacts to DB only on explicit user approval. Accepts partial updates:

```python
class SaveArtifactsRequest(BaseModel):
    business_analysis: dict | None = None
    prd: dict | None = None
    architecture: dict | None = None
    tasks: dict | None = None

@app.post("/project/{project_id}/save-artifacts")
async def save_artifacts(project_id: str, body: SaveArtifactsRequest):
    # Only writes fields that are explicitly provided (not None)
    ...
    return await store.save(project)
```

### 3. New endpoint: `GET /projects`

Returns all saved projects (newest first) — powers the front-end Saved Projects panel:

```python
@app.get("/projects", response_model=list[Project])
async def list_projects():
    return await store.list_all()
```

### 4. New endpoint: `DELETE /project/{id}`

Removes a project from the database:

```python
@app.delete("/project/{project_id}")
async def delete_project(project_id: str):
    project = await _get_project_or_404(project_id)
    await store.delete(project_id)
    return {"deleted": project_id, "idea": project.idea}
```

### 5. LLM timeout fix

In `services/llm_router/router.py`:

```python
# Before
async with httpx.AsyncClient(timeout=60.0) as client:

# After
async with httpx.AsyncClient(timeout=300.0) as client:
```

---

## Frontend Changes (`apps/web/lib/api.ts`)

Three new exported functions:

| Function | HTTP Call | Purpose |
|----------|-----------|---------|
| `saveProjectArtifacts(id, payload)` | `POST /project/{id}/save-artifacts` | Persist reviewed artifacts |
| `listProjects()` | `GET /projects` | Fetch all saved projects |
| `deleteProject(id)` | `DELETE /project/{id}` | Remove a project |

New TypeScript types:

```typescript
export type SaveArtifactsPayload = {
  business_analysis?: BusinessAnalysis | null;
  prd?: PRD | null;
  architecture?: Architecture | null;
  tasks?: Tasks | null;
};
```

The `Project` type also gained `created_at` and `updated_at` fields (returned by the DB).

---

## Frontend Changes (`apps/web/components/ControlPanel.tsx`)

### New UI sections (top to bottom)

```
┌────────────────────────────────────────┐
│  ▶ Saved Projects (N)                  │  ← collapsible panel
│    [idea-1] [Load] [Delete]            │
│    [idea-2] [Load] [Delete]            │
├────────────────────────────────────────┤
│  Project Idea                          │
│  [textarea] [Create Project]           │
├────────────────────────────────────────┤
│  Project: "..." | ID: xxxx  ✓ Saved    │
│  [Run All Agents]                      │
│  [Business][Product][Architect][Planner]│
│                                         │
│  ⚠ Preview mode — artifacts NOT saved  │  ← shown when hasArtifacts && !savedToDb
│  [✓ Approve & Save to Database]        │
│  [✏ Edit Artifacts (JSON)]             │
│                                         │
│  ✓ Artifacts saved to database          │  ← shown when savedToDb
├────────────────────────────────────────┤
│  Project Artifacts                     │
│  Business Analysis                     │
│  Product Requirements (PRD)            │
│  Architecture                          │
│  Implementation Tasks                  │
└────────────────────────────────────────┘
```

### Key state variables

| Variable | Type | Purpose |
|----------|------|---------|
| `savedToDb` | `boolean` | Whether current project is persisted |
| `saving` | `boolean` | Loading state for save-artifacts call |
| `savedProjects` | `Project[]` | Cached list from `GET /projects` |
| `showSavedProjects` | `boolean` | Collapse toggle for the panel |
| `editableJson` | `string` | JSON string in the edit textarea |
| `editMode` | `boolean` | Show editable textarea instead of structured views |

### User flow

1. **Create project** → stored in DB (row with `idea` only)
2. **Run agents** (individual or "Run All") → results appear in preview, **NOT saved**
3. **Review artifacts** in structured view or Raw JSON
4. ***(Optional)*** Click "Edit Artifacts (JSON)" → edit the JSON directly in a textarea
5. **Click "Approve & Save to Database"** → `POST /save-artifacts` persists all artifacts
6. Green confirmation bar: "✓ Artifacts saved to database"
7. Saved project appears in the **Saved Projects** panel

### Saved Projects panel

- Toggle open to fetch `GET /projects`
- Each row shows the project idea, creation date, and whether it has saved artifacts
- **Load** → `GET /project/{id}` → populates the full UI for review/re-export
- **Delete** → removes from DB and refreshes the list

---

## Data Flow Diagram

```
User enters idea
       │
       ▼
POST /project/create ───────────────► PostgreSQL (idea only)
       │
       ▼
User clicks "Run All" or individual agent button
       │
       ▼
GET /project/{id}/run-all (SSE, native EventSource)  or  POST /agent/{name}/{id}
       │                                        │
       │  ML agents run (no DB writes)          │
       ▼                                        ▼
Project returned in-memory ───► UI renders artifacts for preview
       │
       │  User reviews, edits JSON if needed
       ▼
User clicks "Approve & Save to Database"
       │
       ▼
POST /project/{id}/save-artifacts ───► PostgreSQL (artifacts persisted)
       │
       ▼
Green confirmation, panel refreshes
```

---

## Testing

All **12 existing tests pass** (`pytest tests/ -v`):

```
tests/test_export.py::test_export_creates_markdown_files           PASSED
tests/test_router_config.py::test_routing_business_uses_kimi       PASSED
tests/test_store.py::test_create_and_retrieve                      PASSED
tests/test_store.py::test_agent_artifacts_are_persisted            PASSED
... 12 passed in 0.12s
```

No new tests were added — the existing test suite covers the store layer, and the new endpoints follow the same patterns.

---

## How to Restart

```bash
# Terminal 1 — backend (port 8100)
source venv/bin/activate && PYTHONPATH=. uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8100

# Terminal 2 — frontend (port 3000)
cd apps/web && npm run dev
```
