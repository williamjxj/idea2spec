#!/usr/bin/env python3
"""CLI for AI Project CTO — create project, run agents, export workspace."""

import argparse
import asyncio
import json
import sys
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


async def run_pipeline(store: ProjectStore, idea: str, agents: list[str], export: bool) -> Project:
    router = LLMRouter()
    project = store.create(idea)
    print(f"Created project {project.id}\n")

    for agent in agents:
        print(f"Running {agent} agent...")
        try:
            project = await run_single_agent(agent, project, router)  # type: ignore[arg-type]
            store.save(project)
        except LLMRouterError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        print(f"  Done.\n")

    print(json.dumps(project.model_dump(), indent=2))

    if export:
        path = export_project_workspace(project, ROOT / "projects")
        print(f"\nExported workspace to: {path}")

    return project


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
