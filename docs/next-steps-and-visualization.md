# AI Project CTO — Next Steps & Visualization Roadmap

Brief summary of product analysis and visualization feature design (June 2026).

---

## Current State (v0.2 — June 2026)

All core MVP features are complete. The project has progressed beyond the initial gaps.

| Layer | Status |
|-------|--------|
| Business → Product → Architect → Planner agents | Implemented |
| SQLite persistence (aiosqlite) | ✅ Working — survives restarts |
| Preview-&-Approve flow | ✅ Agents run without auto-save; explicit approve step |
| Project list / load / delete | ✅ Saved Projects panel in UI + `GET /projects` + `DELETE /project/{id}` |
| Run-all-agents UI | ✅ SSE stream with live status badges, elapsed timers, LLM provider info |
| Per-agent status tracking | ✅ Status rows show Pending / Running+elapsed timer / Done / Failed |
| SSE direct connection | ✅ SSE bypasses Next.js proxy via `NEXT_PUBLIC_SSE_URL` to avoid buffering |
| LLM-powered project titles | ✅ Auto-generated titles (e.g. "build a habit tracker" → "Daily Habit Tracker") |
| Clean reset script | ✅ `scripts/reset.sh` wipes DB + projects (`make reset`) |
| Editable JSON preview | ✅ Raw JSON editor before approving |
| Export formats | ✅ Markdown workspace + HTML report + Mermaid architecture diagram |
| CLI pipeline | ✅ Linear LangGraph pipeline; supports `--agents` filter |
| Tests | 12 passing (store, export, router config) |

---

## LLM Routing (Cloud Only)

No Ollama/local models in the current implementation. All calls use OpenAI-compatible APIs via `services/llm_router/`.

| Agent | Provider | Default Model | Temperature |
|-------|----------|---------------|-------------|
| Business Analyst | Kimi (Moonshot) | `kimi-k2.5` | 1.0 |
| Product Manager | DeepSeek | `deepseek-v4-pro` | 0.3 |
| Architect | DeepSeek | `deepseek-v4-pro` | 0.3 |
| Engineering Planner | MiniMax | `MiniMax-M2.5` | 0.3 |
| Fallback (missing key) | DeepSeek | `deepseek-v4-pro` | 0.3 |

Configure via `.env`: `KIMI_API_KEY`, `DEEPSEEK_API_KEY`, `MINIMAX_API_KEY`.

---

## Recommended Product Roadmap

### 🟢 Completed in v0.2

- [x] **Run-all-agents UI** — SSE stream in the ControlPanel; individual agent buttons too
- [x] **Per-agent status tracking** — live badges (Pending/Running+elapsed/Done/Failed) with LLM info
- [x] **SSE direct connection** — bypasses Next.js proxy buffering for real-time status updates
- [x] **LLM-powered project titles** — auto-generated from idea text
- [x] **Clean reset** — `scripts/reset.sh` wipes DB + projects (`make reset`)
- [x] **Persistence** — SQLite via aiosqlite; projects survive restarts (see `data/projects.db`)
- [x] **Project list** — Saved Projects panel with load/delete
- [x] **End-to-end validation** — create → all 4 agents → approve → export
- [x] **Human-in-the-loop refinement** — agents output to preview; explicit "Approve & Save" button; editable JSON textarea

### Tier 2 — Usable across sessions

4. ~~Persistence~~ ✅ Done (SQLite)
5. ~~Project list~~ ✅ Done (Saved Projects panel)

### Tier 3 — Differentiation

6. **GitHub integration** — export tasks as issues or scaffold repo
7. **Clerk auth** — required for teams/agencies
8. **Markdown workspace viewer** — structured markdown rendering in the UI (currently raw JSON)
9. **Re-run single agent** — re-run one agent after editing its artifact slice

### Explicitly out of scope (for now)

- Coding agent
- Ollama / local models
- RAG / pgvector
- NotebookLM Enterprise (heavy GCP setup)

---

## New Feature: Workspace Visualization

Transform exported markdown in `projects/<slug>-<id>/` into visual artifacts.

### Build order

| Phase | Output | Effort |
|-------|--------|--------|
| 1 — Diagrams | PNG/SVG per topic | Low |
| 2 — Slides | `.pptx` pitch deck | Medium |
| 3 — HTML | Self-contained infographic page | Medium |
| 4 — Video | MP4 narrated overview | High |

### API strategy

**Hybrid local-first:** open-source renderers by default; optional paid APIs (Gamma, ElevenLabs) behind env flags.

- **Local:** Mermaid (`mermaid-cli-python`), PPTX (`md2ppt` / `markdown-pptx`)
- **Optional premium:** Gamma API for polished decks; Edge TTS / ElevenLabs for video
- **Skip v1:** NotebookLM Enterprise, Obsidian desktop runtime

### Per-artifact mapping

| Source MD | Visual output |
|-----------|---------------|
| `01-business.md` | Competitor landscape (Mermaid mindmap) |
| `02-prd.md` | Feature matrix → slide deck section |
| `03-architecture.md` | System diagram (Mermaid flowchart) |
| `04-roadmap.md` | Timeline / gantt |
| `05-tasks.md` | Epic → issue breakdown |
| All files | Optional `.canvas` (JSON Canvas for Obsidian import) |

### Output layout

```text
projects/<slug>-<id>/
  00-overview.md … 05-tasks.md
  visuals/
    diagrams/
      business-competitors.png
      architecture-system.svg
      roadmap-timeline.png
      tasks-breakdown.png
    deck.pptx              # Phase 2
    index.html             # Phase 3
    overview.mp4           # Phase 4
    manifest.json
```

---

## Parallel Execution Model

**Use `asyncio.gather()` per topic — not git worktrees or Cursor subagents.**

Each markdown file is an independent visualization job. Run up to 5 LLM calls in parallel, then render diagrams with a semaphore (cap 2–3 concurrent Playwright/Mermaid renders).

| Topic | Viz LLM | Provider |
|-------|---------|----------|
| Business | `viz_business` | Kimi |
| PRD | `viz_prd` | DeepSeek |
| Architecture | `viz_architecture` | DeepSeek |
| Roadmap | `viz_roadmap` | DeepSeek |
| Tasks | `viz_tasks` | MiniMax |
| Overview | None | Static status only |

**Sequential steps:** pitch deck assembly, HTML index, and video render aggregate all topics and run after parallel diagram jobs complete.

**Failure isolation:** per-topic errors recorded in `manifest.json`; one bad diagram does not block others.

---

## External Tools Evaluated

| Tool | Verdict |
|------|---------|
| Gamma API | Best premium slides; optional Phase 2 |
| md2ppt / markdown-pptx | Best local PPTX |
| mermaid-cli-python | Best local diagrams |
| NotebookLM Enterprise | Enterprise-only; defer |
| Obsidian API | No headless export; generate `.canvas` files instead |
| video_explainer / Remotion | High quality but overkill for MVP |

---

## Related Docs

- [System overview v0.1](requirements/chatgpt-1.md)
- [Implementation log v0.2](requirements/chatgpt-2.md)
- [MVP design spec](superpowers/specs/2026-06-24-ai-project-cto-design.md)
- [Tech stack reference](tech-stack.md)
- Full implementation plan: `.cursor/plans/workspace_visualization_pipeline_3d3058e4.plan.md`
