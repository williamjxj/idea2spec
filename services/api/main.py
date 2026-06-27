import asyncio
import io
import json
import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from packages.schemas import Project
from services.agent_runtime import run_single_agent
from services.api import db
from services.api.export import export_project_html, export_project_workspace, generate_architecture_mermaid
from services.api.store import store
from services.llm_router import LLMRouter, LLMRouterError
from services.llm_router.config import TaskType

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        await db.run_migrations()
    except Exception as exc:
        msg = f"Database setup failed: {exc}"
        print(f"ERROR: {msg}")
        raise
    yield
    await db.close_db()


app = FastAPI(title="AI Project CTO", version="0.1.0", lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = LLMRouter()

AgentName = Literal["business", "product", "architect", "planner"]


class CreateProjectRequest(BaseModel):
    idea: str


class ExportResponse(BaseModel):
    path: str
    project: Project


async def _get_project_or_404(project_id: str) -> Project:
    project = await store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/project/create", response_model=Project)
async def create_project(body: CreateProjectRequest):
    if not body.idea.strip():
        raise HTTPException(status_code=400, detail="Idea cannot be empty")
    project = await store.create(body.idea.strip())

    # Generate a concise title from the idea using the LLM
    try:
        title = await _generate_project_title(project.idea, router)
        project.title = title
        await store.save(project)
    except Exception:
        # Fallback: extract a readable title heuristically
        project.title = _extract_project_title(project.idea)
        await store.save(project)

    return project


async def _generate_project_title(idea: str, router_: LLMRouter) -> str:
    """Use the fallback LLM to produce a short, professional project name."""
    prompt = (
        "Generate a concise, professional project title (maximum 40 characters, "
        "3-6 words preferred) from the idea below. "
        "Return ONLY the title — no quotes, no explanation, no markdown.\n\n"
        f'Idea: "{idea}"\nTitle:'
    )
    system = "You are a naming assistant. Output ONLY the title, nothing else."
    try:
        text = await router_._chat(TaskType.FALLBACK, system, prompt, retry_on_parse_error=False)
        text = text.strip().strip('"').strip("'").strip(".").strip()
        if 2 <= len(text) <= 60:
            return text
    except Exception:
        pass
    return _extract_project_title(idea)


def _extract_project_title(idea: str) -> str:
    """Heuristic fallback: strip common lead-in phrases and capitalize."""
    import re
    title = idea.strip()
    patterns = [
        r"^i\s+(want\s+to\s+)?(build|create|make|develop|design)\s+(a\s+|an\s+|the\s+)?",
        r"^i\s+need\s+(a\s+|an\s+|the\s+)?",
        r"^can\s+you\s+(help\s+(me\s+)?)?(build|create|make)\s+(a\s+|an\s+|the\s+)?",
        r"^let'?s?\s+(build|create|make)\s+(a\s+|an\s+|the\s+)?",
        r"^create\s+(a\s+|an\s+|the\s+)?",
        r"^build\s+(a\s+|an\s+|the\s+)?",
    ]
    for pattern in patterns:
        title = re.sub(pattern, "", title, flags=re.IGNORECASE).strip()
    if not title:
        title = idea
    # Capitalize first letter
    title = title[0].upper() + title[1:] if title else idea
    return title


@app.get("/project/{project_id}", response_model=Project)
async def get_project(project_id: str):
    return await _get_project_or_404(project_id)


AGENT_TIMEOUT = 120  # seconds


async def _run_agent(project_id: str, agent: AgentName) -> Project:
    """Run a single agent and return the result WITHOUT saving to DB.

    The returned project contains the agent output in-memory.  Call
    POST /project/{id}/save-artifacts to persist it.
    Times out after AGENT_TIMEOUT seconds.
    """
    project = await _get_project_or_404(project_id)
    try:
        updated = await asyncio.wait_for(
            run_single_agent(agent, project, router),
            timeout=AGENT_TIMEOUT,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=f"Agent '{agent}' timed out after {AGENT_TIMEOUT}s — LLM call took too long. Check your API keys and try again.",
        ) from exc
    except LLMRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return updated


@app.post("/agent/business/{project_id}", response_model=Project)
async def agent_business(project_id: str):
    return await _run_agent(project_id, "business")


@app.post("/agent/product/{project_id}", response_model=Project)
async def agent_product(project_id: str):
    return await _run_agent(project_id, "product")


@app.post("/agent/architect/{project_id}", response_model=Project)
async def agent_architect(project_id: str):
    return await _run_agent(project_id, "architect")


@app.post("/agent/planner/{project_id}", response_model=Project)
async def agent_planner(project_id: str):
    return await _run_agent(project_id, "planner")


@app.post("/project/{project_id}/export", response_model=ExportResponse)
async def export_project(project_id: str):
    project = await _get_project_or_404(project_id)
    path = export_project_workspace(project)
    await store.save(project)
    return ExportResponse(path=str(path), project=project)


EXPORT_FORMATS = {"markdown", "html", "mermaid"}


@app.get("/project/{project_id}/export/zip")
async def download_export_zip(
    project_id: str,
    format: str = Query("markdown", description="Export format: markdown, html, mermaid"),
):
    project = await _get_project_or_404(project_id)
    if format not in EXPORT_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Choose from {EXPORT_FORMATS}")

    if format == "markdown":
        out_dir = export_project_workspace(project)
        ext = "md"
    elif format == "html":
        out_dir = export_project_html(project)
        ext = "html"
    elif format == "mermaid":
        out_dir = export_project_html(project)  # still generate markdown for context
        mermaid_content = generate_architecture_mermaid(project)
        mermaid_path = out_dir / "architecture.mmd"
        mermaid_path.write_text(mermaid_content, encoding="utf-8")
        ext = "mmd"

    await store.save(project)

    zip_buffer = io.BytesIO()
    archive_path = shutil.make_archive(str(out_dir), "zip", root_dir=out_dir)
    with open(archive_path, "rb") as f:
        zip_buffer.write(f.read())
    os.unlink(archive_path)
    zip_buffer.seek(0)

    filename = f"{out_dir.name}.{ext}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


ALL_AGENTS: list[AgentName] = ["business", "product", "architect", "planner"]


def _sse_event(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@app.get("/project/{project_id}/run-all")
async def run_all_agents(project_id: str):
    """Run all agents sequentially; yields SSE events but does NOT save to DB.

    Use GET for native EventSource compatibility on the frontend.
    Use POST /project/{id}/save-artifacts after reviewing to persist.
    """
    project = await _get_project_or_404(project_id)

    async def event_stream():
        nonlocal project

        for agent in ALL_AGENTS:
            yield _sse_event("agent_start", {"agent": agent})
            try:
                project = await asyncio.wait_for(
                    run_single_agent(agent, project, router),
                    timeout=AGENT_TIMEOUT,
                )
            except (LLMRouterError, asyncio.TimeoutError) as exc:
                yield _sse_event("agent_error", {"agent": agent, "error": str(exc)})
                return
            yield _sse_event("agent_complete", {"agent": agent})
            await asyncio.sleep(0)  # yield control to event loop between agents
        yield _sse_event("complete", {"project": project.model_dump(mode="json")})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx: disable buffering
        },
    )


class SaveArtifactsRequest(BaseModel):
    business_analysis: dict | None = None
    prd: dict | None = None
    architecture: dict | None = None
    tasks: dict | None = None


class SaveArtifactsResponse(BaseModel):
    project: Project
    export_path: str


@app.post("/project/{project_id}/save-artifacts", response_model=SaveArtifactsResponse)
async def save_artifacts(project_id: str, body: SaveArtifactsRequest):
    """Save or update project artifacts to SQLite AND export markdown to filesystem.

    Accepts partial updates — only the fields provided are written.
    Use after reviewing agent output in the UI.
    """
    from packages.schemas import BusinessAnalysis, PRD, Architecture, Tasks

    project = await _get_project_or_404(project_id)

    if body.business_analysis is not None:
        project.business_analysis = BusinessAnalysis.model_validate(body.business_analysis)
    if body.prd is not None:
        project.prd = PRD.model_validate(body.prd)
    if body.architecture is not None:
        project.architecture = Architecture.model_validate(body.architecture)
    if body.tasks is not None:
        project.tasks = Tasks.model_validate(body.tasks)

    # 1. Persist to SQLite
    project = await store.save(project)

    # 2. Export markdown to filesystem (projects/<slug>-<id>/)
    export_path = export_project_workspace(project)
    # The export appended to project.exports — save that too
    project = await store.save(project)

    return SaveArtifactsResponse(project=project, export_path=str(export_path))


@app.get("/projects", response_model=list[Project])
async def list_projects():
    """Return all saved projects, newest first."""
    return await store.list_all()


@app.delete("/project/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and its artifacts from the database."""
    project = await _get_project_or_404(project_id)
    await store.delete(project_id)
    return {"deleted": project_id, "idea": project.idea}
