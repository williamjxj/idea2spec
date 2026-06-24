import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from packages.schemas import Project
from services.agent_runtime import run_single_agent
from services.api.export import export_project_workspace
from services.api.store import store
from services.llm_router import LLMRouter, LLMRouterError

load_dotenv()

app = FastAPI(title="AI Project CTO", version="0.1.0")

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


def _get_project_or_404(project_id: str) -> Project:
    project = store.get(project_id)
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
    return store.create(body.idea.strip())


@app.get("/project/{project_id}", response_model=Project)
async def get_project(project_id: str):
    return _get_project_or_404(project_id)


async def _run_agent(project_id: str, agent: AgentName) -> Project:
    project = _get_project_or_404(project_id)
    try:
        updated = await run_single_agent(agent, project, router)
    except LLMRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return store.save(updated)


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
    project = _get_project_or_404(project_id)
    path = export_project_workspace(project)
    return ExportResponse(path=str(path), project=project)
