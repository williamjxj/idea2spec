import json
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable
from uuid import uuid4

import asyncpg

from packages.schemas import Project
from services.api import db


@runtime_checkable
class ProjectStoreProtocol(Protocol):
    """Abstract interface for project storage — enables mock swapping in tests."""

    async def create(self, idea: str) -> Project:
        ...

    async def get(self, project_id: str) -> Optional[Project]:
        ...

    async def save(self, project: Project) -> Project:
        ...

    async def list_all(self) -> list[Project]:
        ...


def _project_from_row(row: asyncpg.Record | None) -> Project | None:
    if row is None:
        return None
    data = dict(row)
    # asyncpg returns UUID as Python UUID object; Project.id expects str
    if "id" in data and not isinstance(data["id"], str):
        data["id"] = str(data["id"])
    # Deserialize JSONB columns from str back to Python objects
    for col in ("business_analysis", "prd", "architecture", "tasks", "exports"):
        if isinstance(data.get(col), str):
            data[col] = json.loads(data[col])
    return Project.model_validate(data)


class ProjectStore:
    """Postgres-backed project store. All methods are async."""

    def __init__(self) -> None:
        self._pool_ref: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool_ref is None:
            self._pool_ref = await db.get_pool()
        return self._pool_ref

    async def create(self, idea: str) -> Project:
        pool = await db.get_pool()
        project = Project(
            id=str(uuid4()),
            idea=idea,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await pool.execute(
            """
            INSERT INTO projects (id, idea, business_analysis, prd, architecture, tasks, exports, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            project.id,
            project.idea,
            _jsonb(project.business_analysis),
            _jsonb(project.prd),
            _jsonb(project.architecture),
            _jsonb(project.tasks),
            _jsonb(project.exports),
            project.created_at,
            project.updated_at,
        )
        return project

    async def get(self, project_id: str) -> Project | None:
        pool = await db.get_pool()
        row = await pool.fetchrow(
            "SELECT * FROM projects WHERE id = $1", project_id
        )
        return _project_from_row(row)

    async def save(self, project: Project) -> Project:
        pool = await db.get_pool()
        project.updated_at = datetime.now(timezone.utc)
        await pool.execute(
            """
            UPDATE projects
            SET idea = $1, business_analysis = $2, prd = $3, architecture = $4,
                tasks = $5, exports = $6, updated_at = $7
            WHERE id = $8
            """,
            project.idea,
            _jsonb(project.business_analysis),
            _jsonb(project.prd),
            _jsonb(project.architecture),
            _jsonb(project.tasks),
            _jsonb(project.exports),
            project.updated_at,
            project.id,
        )
        return project

    async def list_all(self) -> list[Project]:
        pool = await db.get_pool()
        rows = await pool.fetch("SELECT * FROM projects ORDER BY created_at DESC")
        return [_project_from_row(r) for r in rows if r is not None]


def _jsonb(value: object) -> str | None:
    """Serialize a Pydantic model (or list, or None) to JSON string for JSONB."""
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(mode="json"), default=str)
    if isinstance(value, list):
        return json.dumps([_serialize_item(v) for v in value], default=str)
    return json.dumps(value, default=str)


def _serialize_item(value: object) -> object:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


class InMemoryStore:
    """In-memory store that implements ProjectStoreProtocol — used in tests."""

    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}

    async def create(self, idea: str) -> Project:
        project = Project(id=str(uuid4()), idea=idea)
        self._projects[project.id] = project
        return project

    async def get(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    async def save(self, project: Project) -> Project:
        self._projects[project.id] = project
        return project

    async def list_all(self) -> list[Project]:
        return list(self._projects.values())


store: ProjectStoreProtocol = ProjectStore()
