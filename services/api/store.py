import json
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable
from uuid import uuid4

import aiosqlite

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row: aiosqlite.Row) -> dict:
    """Convert an aiosqlite Row (dict-like) into a plain dict."""
    return dict(row)


def _project_from_row(row: aiosqlite.Row | None) -> Project | None:
    if row is None:
        return None
    data = _row_to_dict(row)
    # Ensure id is a str
    data["id"] = str(data["id"])
    # Deserialize JSON columns (stored as TEXT in SQLite) back to Python objects
    for col in ("business_analysis", "prd", "architecture", "tasks", "exports"):
        if isinstance(data.get(col), str):
            data[col] = json.loads(data[col])
        elif data.get(col) is None:
            # SQLite stores empty arrays as NULL → default to empty list where expected
            if col == "exports":
                data[col] = []
    return Project.model_validate(data)


def _json_dumps(value: object) -> str | None:
    """Serialize a Pydantic model (or list, or None) to JSON string for TEXT column."""
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


# ---------------------------------------------------------------------------
# SQLite-backed project store
# ---------------------------------------------------------------------------

class ProjectStore:
    """SQLite-backed project store using aiosqlite for async access."""

    # ── helpers ──────────────────────────────────────────────────────

    async def _execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        conn = await db.get_connection()
        cur = await conn.execute(sql, params) if params else await conn.execute(sql)
        await conn.commit()
        return cur

    async def create(self, idea: str) -> Project:
        project = Project(
            id=str(uuid4()),
            idea=idea,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await self._execute(
            """INSERT INTO projects (id, idea, business_analysis, prd, architecture, tasks, exports, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project.id,
                project.idea,
                _json_dumps(project.business_analysis),
                _json_dumps(project.prd),
                _json_dumps(project.architecture),
                _json_dumps(project.tasks),
                _json_dumps(project.exports),
                project.created_at.isoformat(),
                project.updated_at.isoformat(),
            ),
        )
        return project

    async def get(self, project_id: str) -> Project | None:
        conn = await db.get_connection()
        cur = await conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cur.fetchone()
        if row is None:
            return None
        return _project_from_row(row)

    async def save(self, project: Project) -> Project:
        project.updated_at = datetime.now(timezone.utc)
        conn = await db.get_connection()
        await conn.execute(
            """UPDATE projects
               SET idea = ?, business_analysis = ?, prd = ?, architecture = ?,
                   tasks = ?, exports = ?, updated_at = ?
               WHERE id = ?""",
            (
                project.idea,
                _json_dumps(project.business_analysis),
                _json_dumps(project.prd),
                _json_dumps(project.architecture),
                _json_dumps(project.tasks),
                _json_dumps(project.exports),
                project.updated_at.isoformat(),
                project.id,
            ),
        )
        await conn.commit()
        return project

    async def list_all(self) -> list[Project]:
        conn = await db.get_connection()
        cur = await conn.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = await cur.fetchall()
        if not rows:
            return []
        return [_project_from_row(r) for r in rows]

    async def delete(self, project_id: str) -> None:
        conn = await db.get_connection()
        await conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await conn.commit()


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
