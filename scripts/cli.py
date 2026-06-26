#!/usr/bin/env python3
"""CLI for AI Project CTO — create project, run agents, export workspace."""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from packages.schemas import Project
from services.agent_runtime import run_single_agent
from services.api.export import export_project_workspace
from services.api.store import ProjectStore
from services.llm_router import LLMRouter, LLMRouterError


SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


async def _run_with_spinner(agent: str, project: Project, router: LLMRouter) -> Project:
    """Run an agent with a single-line spinner to show it's alive."""
    loop = asyncio.get_running_loop()
    agent_task = asyncio.create_task(run_single_agent(agent, project, router))
    t0 = time.monotonic()
    idx = 0
    while not agent_task.done():
        elapsed = time.monotonic() - t0
        ch = SPINNER[idx % len(SPINNER)]
        print(f"  {ch} {agent} agent... ({elapsed:.0f}s)", end="\r", flush=True)
        idx += 1
        await asyncio.sleep(0.3)
    print(" " * 60, end="\r", flush=True)  # clear spinner line
    return await agent_task


async def run_pipeline(store: ProjectStore, idea: str, agents: list[str], export: bool) -> Project:
    router = LLMRouter()
    project = await store.create(idea)
    print(f"Created project {project.id}\n")

    for agent in agents:
        t0 = time.monotonic()
        try:
            project = await _run_with_spinner(agent, project, router)  # type: ignore[arg-type]
            await store.save(project)
        except LLMRouterError as exc:
            print(f"[{_ts()}] Error: {exc}", file=sys.stderr)
            sys.exit(1)
        elapsed = time.monotonic() - t0
        print(f"[{_ts()}]   Done. ({elapsed:.1f}s)\n")

    print(json.dumps(project.model_dump(mode="json"), indent=2))

    if export:
        path = export_project_workspace(project, ROOT / "projects")
        print(f"\nExported workspace to: {path}")

    return project


def _ts() -> str:
    return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


def main():
    parser = argparse.ArgumentParser(description="AI Project CTO CLI")
    parser.add_argument("idea", help="Project idea")
    parser.add_argument(
        "--agents",
        default="business,product,architect,planner",
        help="Comma-separated agents to run (default: all)",
    )
    parser.add_argument("--export", action="store_true", help="Export markdown workspace")
    args = parser.parse_args()

    agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    store = ProjectStore()
    asyncio.run(run_pipeline(store, args.idea, agents, args.export))


if __name__ == "__main__":
    main()
