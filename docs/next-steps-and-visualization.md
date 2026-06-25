# AI Project CTO — Next Steps & Visualization Roadmap

Brief summary of product analysis and visualization feature design (June 2026).

---

## Current State (MVP v0.1)

The core engine is done: four agents, FastAPI backend, Next.js control panel, markdown workspace export, and CLI full pipeline.

| Layer | Status |
|-------|--------|
| Business → Product → Architect → Planner agents | Implemented |
| In-memory project store | Working (lost on restart) |
| Export to `projects/<slug>-<id>/` | Working |
| Tests | Minimal (router config + export) |

**Gap:** Users often stop halfway through the pipeline. Example export had Business + PRD done, but Architecture and Tasks were `_Not yet generated._` — the bottleneck is UX/workflow completion, not agent capability.

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

Prioritized from existing plans (`docs/requirements/chatgpt-1.md`, `chatgpt-2.md`, design spec):

### Tier 1 — Finish the MVP experience

1. **Run-all-agents UI** — mirror CLI pipeline; show artifact readiness before export
2. **Markdown workspace viewer** — replace/supplement raw JSON dump in the control panel
3. **End-to-end validation** — create → all 4 agents → export

### Tier 2 — Usable across sessions

4. **Persistence** (Supabase/Postgres) — projects survive restarts
5. **Project list** — load, delete, optionally fork

### Tier 3 — Differentiation

6. **GitHub integration** — export tasks as issues or scaffold repo
7. **Clerk auth** — required for teams/agencies
8. **Human-in-the-loop refinement** — re-run one agent after editing a slice

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
