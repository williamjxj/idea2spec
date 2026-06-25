import os
from pathlib import Path

import asyncpg

_pool: asyncpg.Pool | None = None


def _dsn() -> str:
    return os.getenv(
        "DATABASE_URL",
        f"postgresql://{os.getenv('PGUSER', 'postgres')}:{os.getenv('PGPASSWORD', 'postgres')}"
        f"@{os.getenv('PGHOST', 'localhost')}:{os.getenv('PGPORT', '5432')}"
        f"/{os.getenv('PGDATABASE', 'ai_project_cto')}",
    )


async def init_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=_dsn(), min_size=2, max_size=10)
    return _pool


async def get_pool() -> asyncpg.Pool:
    if _pool is None:
        return await init_db_pool()
    return _pool


async def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def run_migrations() -> None:
    """Run scripts/init_db.sql to ensure schema exists."""
    pool = await get_pool()
    sql_path = Path(__file__).resolve().parents[2] / "scripts" / "init_db.sql"
    sql = sql_path.read_text()
    async with pool.acquire() as conn:
        await conn.execute(sql)
