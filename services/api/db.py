import os
from pathlib import Path

import aiosqlite

_connection: aiosqlite.Connection | None = None


def _db_path() -> Path:
    """Return the path to the local SQLite database file."""
    env_path = os.getenv("DATABASE_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[2] / "data" / "projects.db"


async def get_connection() -> aiosqlite.Connection:
    """Return the shared async SQLite connection — creates if needed."""
    global _connection
    if _connection is None:
        db_file = _db_path()
        db_file.parent.mkdir(parents=True, exist_ok=True)
        _connection = await aiosqlite.connect(str(db_file))
        _connection.row_factory = aiosqlite.Row
        await _connection.execute("PRAGMA journal_mode=WAL")
        await _connection.execute("PRAGMA foreign_keys=ON")
    return _connection


async def run_migrations() -> None:
    """Run init_db.sql to ensure the schema exists, then apply any ALTER TABLE migrations."""
    conn = await get_connection()
    sql_path = Path(__file__).resolve().parents[2] / "scripts" / "init_db.sql"
    sql = sql_path.read_text()
    for statement in sql.split(";"):
        stmt = statement.strip()
        if stmt:
            await conn.execute(stmt)
    await conn.commit()

    # Add `title` column if it does not exist yet (migration for existing DBs)
    try:
        await conn.execute("ALTER TABLE projects ADD COLUMN title TEXT NOT NULL DEFAULT ''")
        await conn.commit()
        print("INFO: Added `title` column to projects table (migration)")
    except Exception:
        # Column already exists — ignore
        pass


async def close_db() -> None:
    """Close the database connection."""
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
