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

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        await db.run_migrations()
    except (ConnectionRefusedError, OSError) as exc:
        msg = (
            f"Cannot connect to PostgreSQL: {exc}\n\n"
            "Make sure PostgreSQL is running:\n"
            "  docker start ai-project-cto-db   # if stopped\n"
            "  make db                          # create and start a fresh container\n\n"
            "Then restart the API."
        )
        print(f"ERROR: {msg}")
        raise  # keeps FastAPI from starting — DB is required
    yield
    await db.close_db_pool()


app = FastAPI(title="AI Project CTO", version="0.1.0", lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
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
    return await store.create(body.idea.strip())


@app.get("/project/{project_id}", response_model=Project)
async def get_project(project_id: str):
    return await _get_project_or_404(project_id)


async def _run_agent(project_id: str, agent: AgentName) -> Project:
    project = await _get_project_or_404(project_id)
    try:
        updated = await run_single_agent(agent, project, router)
    except LLMRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return await store.save(updated)


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


@app.post("/project/{project_id}/run-all")
async def run_all_agents(project_id: str):
    project = await _get_project_or_404(project_id)

    async def event_stream():
        nonlocal project
        for agent in ALL_AGENTS:
            yield _sse_event("agent_start", {"agent": agent})
            try:
                project = await run_single_agent(agent, project, router)
            except LLMRouterError as exc:
                # Save partial state before failing — preserve successful agents' work
                await store.save(project)
                yield _sse_event("agent_error", {"agent": agent, "error": str(exc)})
                return
            await store.save(project)
            yield _sse_event("agent_complete", {"agent": agent})
        yield _sse_event("complete", {"project": project.model_dump(mode="json")})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
