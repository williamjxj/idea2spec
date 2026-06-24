from pathlib import Path

from slugify import slugify

from packages.schemas import Project


def export_project_workspace(project: Project, base_dir: Path | str = "projects") -> Path:
    root = Path(base_dir)
    slug = slugify(project.idea[:60]) or project.id[:8]
    out = root / f"{slug}-{project.id[:8]}"
    out.mkdir(parents=True, exist_ok=True)

    (out / "00-overview.md").write_text(
        _overview_md(project), encoding="utf-8"
    )
    (out / "01-business.md").write_text(
        _business_md(project), encoding="utf-8"
    )
    (out / "02-prd.md").write_text(_prd_md(project), encoding="utf-8")
    (out / "03-architecture.md").write_text(
        _architecture_md(project), encoding="utf-8"
    )
    (out / "04-roadmap.md").write_text(_roadmap_md(project), encoding="utf-8")
    (out / "05-tasks.md").write_text(_tasks_md(project), encoding="utf-8")
    return out


def _overview_md(project: Project) -> str:
    return f"""# Project Overview

**ID:** {project.id}

## Idea

{project.idea}

## Status

| Artifact | Ready |
|----------|-------|
| Business Analysis | {'Yes' if project.business_analysis else 'No'} |
| PRD | {'Yes' if project.prd else 'No'} |
| Architecture | {'Yes' if project.architecture else 'No'} |
| Tasks | {'Yes' if project.tasks else 'No'} |
"""


def _business_md(project: Project) -> str:
    b = project.business_analysis
    if not b:
        return "# Business Analysis\n\n_Not yet generated._\n"
    competitors = "\n".join(f"- {c}" for c in b.competitors) or "_None listed_"
    return f"""# Business Analysis

## Market

{b.market}

## Competitors

{competitors}

## Monetization

{b.monetization}
"""


def _prd_md(project: Project) -> str:
    p = project.prd
    if not p:
        return "# Product Requirements\n\n_Not yet generated._\n"
    features = "\n".join(f"- {f}" for f in p.features) or "_None_"
    stories = "\n".join(f"- {s}" for s in p.user_stories) or "_None_"
    return f"""# Product Requirements (PRD)

## Features

{features}

## User Stories

{stories}
"""


def _roadmap_md(project: Project) -> str:
    p = project.prd
    if not p or not p.roadmap:
        return "# Roadmap\n\n_Not yet generated._\n"
    items = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(p.roadmap))
    return f"""# Roadmap

{items}
"""


def _architecture_md(project: Project) -> str:
    a = project.architecture
    if not a:
        return "# Architecture\n\n_Not yet generated._\n"
    return f"""# Architecture

## Frontend

{a.frontend}

## Backend

{a.backend}

## Database

{a.database}

## Infrastructure

{a.infra}
"""


def _tasks_md(project: Project) -> str:
    t = project.tasks
    if not t:
        return "# Tasks\n\n_Not yet generated._\n"
    epics = "\n".join(f"- {e}" for e in t.epics) or "_None_"
    issues = "\n".join(f"- {i}" for i in t.issues) or "_None_"
    return f"""# Implementation Tasks

## Epics

{epics}

## Issues

{issues}
"""
