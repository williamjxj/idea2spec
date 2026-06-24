# 📘 AI Project CTO — System Overview (v0.1)

## 1. Product Vision

AI Project CTO is a **multi-agent system that transforms an idea into a structured software project workspace**.

### Core transformation:

```text
Idea
  ↓
Business Analysis
  ↓
Product Requirements (PRD)
  ↓
System Architecture
  ↓
Implementation Tasks
```

The output is not chat.

It is a **structured project artifact system**.

---

## 2. Target Users (Phase 1 → Phase 3)

### Phase 1 (MVP focus)

* Solo founders
* Indie hackers
* Technical freelancers
* Startup builders

### Phase 2

* AI agencies
* Consulting teams
* Software studios

### Phase 3

* Enterprise innovation teams

---

## 3. Core Product Model (Most Important Concept)

Everything revolves around one object:

```ts
Project
```

### Project structure:

```ts
type Project = {
  id: string;
  idea: string;

  business?: {
    market?: string;
    competitors?: string[];
    monetization?: string;
  };

  prd?: {
    features: string[];
    userStories: string[];
    roadmap: string[];
  };

  architecture?: {
    frontend?: string;
    backend?: string;
    database?: string;
    infra?: string;
  };

  tasks?: {
    epics: string[];
    issues: string[];
  };
};
```

### Key principle:

> Agents do NOT chat with users.
> Agents MODIFY this Project object.

---

## 4. System Architecture

### High-level stack

```text
Frontend:
  Next.js + Clerk Auth

Backend:
  FastAPI

Agent Orchestration:
  LangGraph

LLM Layer:
  OpenAI-compatible router

Local Models:
  Ollama (Qwen, DeepSeek, etc.)

Database:
  PostgreSQL + pgvector (Supabase)

Infra:
  Docker + optional Kubernetes
```

---

## 5. LLM Strategy (Cost-Optimized)

### Model Router Pattern

All models are accessed via a unified interface:

```text
Task → Model Selection
```

| Task Type     | Model        |
| ------------- | ------------ |
| Coding / PRD  | Qwen         |
| System design | DeepSeek     |
| Research      | Kimi         |
| fallback      | Ollama local |

### Design goal:

> Swap models without changing system logic.

---

## 6. Agent System (MVP Version)

### Phase 1 Agents (ONLY 4)

#### 1. Business Analyst Agent

* Market analysis
* Competitors
* Monetization strategy

#### 2. Product Manager Agent

* PRD
* Features
* Roadmap
* User stories

#### 3. Architect Agent

* System design
* Database schema
* API design
* Infra design

#### 4. Engineering Planner Agent

* GitHub issues
* Epics
* Tasks
* Implementation breakdown

---

### Important constraint:

> No coding agent in MVP.

Reason:
We optimize for **clarity + structure**, not code generation.

---

## 7. Execution Model (LangGraph)

### State-based workflow:

```text
START
  ↓
Business Agent
  ↓
Product Agent
  ↓
Architect Agent
  ↓
Planner Agent
  ↓
END
```

### State object:

```ts
ProjectState = {
  idea: string,
  project: Project,
  stage: string
}
```

---

## 8. Development Strategy

### Mode: CLI-first (Phase 1)

Reason:

* fastest iteration
* minimal UI distraction
* easier debugging
* better for LangGraph tuning

---

### Phase progression:

#### Phase 1

CLI + FastAPI + LangGraph

#### Phase 2

Next.js dashboard (Project workspace UI)

#### Phase 3

GitHub / MCP integrations

---

## 9. Repository Structure (Monorepo)

```text
ai-project-cto/

apps/
  web/                 # Next.js UI

services/
  api/                 # FastAPI backend
  agent-runtime/       # LangGraph workflows
  llm-router/          # model abstraction

packages/
  schemas/            # Project schema (core)
  prompts/            # agent prompts
  shared/             # utilities

infra/
  docker/
  db/

docs/
```

---

## 10. Development Principles

### Principle 1 — Artifact-first design

Agents output structured data, not chat.

---

### Principle 2 — Deterministic state updates

Each agent only updates part of Project.

---

### Principle 3 — Model independence

LLMs are interchangeable via router.

---

### Principle 4 — Minimal MVP scope

Only 4 agents initially.

---

### Principle 5 — Local-first development

Use:

* MacBook M3
* Ollama
* Docker
* Local FastAPI

Cloud only after MVP works.

---

## 11. Immediate Next Step (Execution Plan)

### Step 1 (NOW)

Initialize repo:

* monorepo structure
* Project schema
* FastAPI skeleton
* LangGraph skeleton
* LLM router stub

---

### Step 2

Implement:

```text
Business Analyst Agent (first working agent)
```

---

### Step 3

Run:

```text
CLI input → Project output (Markdown)
```

---

## 12. Definition of Done (MVP v0.1)

You have success when:

```text
Input:
"I want to build AI Resume SaaS"

Output:
- market analysis
- PRD
- architecture
- task breakdown
```

Stored as structured Project object.

---

# 🔥 Next action (important)

Now we move to **real implementation scaffold**.

Next I will generate:

### 👉 FULL runnable starter repo (copy-paste ready)

Including:

* FastAPI server
* LangGraph first workflow
* Ollama / Qwen integration
* Business Agent (working)
* CLI test script
* Project state persistence (in-memory first)
* LLM router implementation

---


Start with `Minimal MVP` (FASTEST):

* in-memory state
* CLI only
* no DB initially


```text
A → build velocity first
```
