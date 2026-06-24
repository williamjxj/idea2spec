# 📘 AI Project CTO — Implementation Log (v0.2)

## 1. Project Overview

AI Project CTO is a **multi-agent system that converts an idea into a structured software project workspace**.

It is designed as a **workflow engine, not a chatbot**.

---

## 2. Core Value Proposition

```text id="p1k8aa"
Idea → Business Analysis → PRD → Architecture → Tasks → Workspace
```

The system generates **structured software blueprints**, not conversational responses.

---

## 3. System Architecture (Current)

### Full Stack

```text id="x8m1zz"
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

---

## 4. Core Data Model

### Project Object (single source of truth)

```ts id="a2m8bb"
Project = {
  idea: string,

  business_analysis?: {
    market: string;
    competitors: string[];
    monetization: string;
  },

  prd?: {
    features: string[];
    userStories: string[];
    roadmap: string[];
  },

  architecture?: {
    frontend: string;
    backend: string;
    database: string;
    infra: string;
  },

  tasks?: {
    epics: string[];
    issues: string[];
  }
}
```

---

## 5. Agent System (Current Implementation)

### Phase 1 Agents

#### 1. Business Agent

* Market analysis
* Competitors
* Monetization

#### 2. Product Agent

* PRD generation
* Features
* User stories
* MVP roadmap

#### 3. Architect Agent

* System design
* APIs
* database schema
* infrastructure

#### 4. Planner Agent (defined, optional next step)

* task breakdown
* GitHub issues
* execution plan

---

## 6. Execution Mode (LangGraph)

### Current Flow

```text id="c9m2zz"
Business Agent
  ↓
Product Agent
  ↓
Architect Agent
  ↓
(Planner Agent - next phase)
```

### State Handling

* Shared `ProjectState`
* In-memory persistence (MVP)
* Each agent mutates the same object

---

## 7. LLM Strategy (Cost Optimized)

### Model Routing

| Task Type         | Model         |
| ----------------- | ------------- |
| Business Analysis | Qwen (Ollama) |
| Product Reasoning | DeepSeek      |
| Architecture      | DeepSeek      |
| General fallback  | Ollama        |

### Key Principle

> Models are interchangeable via router (OpenAI-compatible abstraction)

---

## 8. Backend API Design (Current)

### Core endpoints

```text id="m8k1aa"
POST /project/create
POST /agent/business/{id}
POST /agent/product/{id}
POST /agent/architect/{id}
```

### Behavior

* Each endpoint triggers one agent
* Updates shared in-memory project state
* Returns updated project object

---

## 9. Frontend (Next.js UI)

### Current UI Capabilities

* Create project from idea input
* Generate project ID
* Run agents individually:

  * Business Agent
  * Product Agent
  * Architect Agent
* View structured JSON output

### UI Type

> Control panel for AI agents (not dashboard yet)

---

## 10. Workspace Generator (Implemented)

### Output format

Each project can be exported as:

```text id="w3k9aa"
projects/<project-name>/

00-overview.md
01-business.md
02-prd.md
03-architecture.md
04-roadmap.md
05-tasks.md
```

### Purpose

Transforms structured agent output into:

> human-readable software blueprint workspace

---

## 11. Current System Behavior

### User Flow

```text id="z2m8cc"
1. User enters idea
2. Creates project
3. Runs Business Agent
4. Runs Product Agent
5. Runs Architect Agent
6. Views evolving project state
```

---

## 12. Key Design Principles

### 1. Artifact-first system

Agents produce structured outputs, not chat.

---

### 2. Human-in-the-loop execution

User controls agent execution step-by-step.

---

### 3. Stateless LLM layer

LLMs are interchangeable via router.

---

### 4. Project is the core object

Everything modifies a single structured Project.

---

### 5. Local-first MVP

No DB, no cloud dependency yet.

---

## 13. What We Have Built So Far

### Completed

* Monorepo architecture design
* LangGraph multi-agent pipeline
* 3 production-style agents
* FastAPI backend
* Next.js control panel UI
* LLM routing system (Qwen / DeepSeek / Ollama)
* Markdown workspace generator
* Interactive agent execution API

---

## 14. Current System Classification

This system is now:

```text id="q9m1dd"
AI Agent Workspace Generator (v0.1 SaaS Core)
```

Not:

* chatbot
* RAG system
* prompt app

---

## 15. Next Recommended Phase

### Next upgrade options:

* Persistence layer (Supabase / Postgres)
* Markdown live workspace UI (Notion-like)
* Planner Agent completion
* GitHub repo generator

---

## 16. Current Status

### System maturity:

```text id="k2m9cc"
MVP Core Engine: ✅ DONE
Agent Pipeline: ✅ DONE
UI Control Panel: ✅ DONE
Workspace Generator: ✅ DONE
Production readiness: ⚠️ EARLY MVP
```
