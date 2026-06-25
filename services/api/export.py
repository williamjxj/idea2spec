from datetime import datetime, timezone
from pathlib import Path

from slugify import slugify

from packages.schemas import ExportArtifact, ExportFile, Project


def export_project_workspace(project: Project, base_dir: Path | str = "projects") -> Path:
    root = Path(base_dir)
    slug = slugify(project.idea[:60]) or project.id[:8]
    out = root / f"{slug}-{project.id[:8]}"
    out.mkdir(parents=True, exist_ok=True)

    files: list[ExportFile] = []

    def _write(name: str, content: str) -> None:
        (out / name).write_text(content, encoding="utf-8")
        files.append(ExportFile(name=name, content=content))

    _write("00-overview.md", _overview_md(project))
    _write("01-business.md", _business_md(project))
    _write("02-prd.md", _prd_md(project))
    _write("03-architecture.md", _architecture_md(project))
    _write("04-roadmap.md", _roadmap_md(project))
    _write("05-tasks.md", _tasks_md(project))

    # Record the export artifact for future diversified output retrieval
    artifact = ExportArtifact(
        format="markdown",
        type="workspace",
        files=files,
        created_at=datetime.now(timezone.utc),
    )
    project.exports.append(artifact)

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


def export_project_html(project: Project, base_dir: Path | str = "projects") -> Path:
    """Export a standalone HTML report of the project."""
    from datetime import datetime, timezone

    root = Path(base_dir)
    slug = slugify(project.idea[:60]) or project.id[:8]
    out = root / f"{slug}-{project.id[:8]}-html"
    out.mkdir(parents=True, exist_ok=True)

    _build_html_report(project, out)

    artifact = ExportArtifact(
        format="html",
        type="workspace-report",
        files=[],
        created_at=datetime.now(timezone.utc),
    )
    project.exports.append(artifact)
    return out


def _build_html_report(project: Project, out_dir: Path) -> None:
    """Generate a single self-contained HTML file with inline CSS."""
    sections = []

    def _section(title: str, body: str) -> str:
        return f'<section><h2>{title}</h2><div class="content">{body}</div></section>'

    status_rows = ""
    for name in ("Business Analysis", "PRD", "Architecture", "Tasks"):
        ready = bool(getattr(project, {"Business Analysis": "business_analysis", "PRD": "prd",
                                       "Architecture": "architecture", "Tasks": "tasks"}[name]))
        cls = "yes" if ready else "no"
        icon = "✓" if ready else "✗"
        status_rows += f'<tr><td>{name}</td><td class="{cls}">{icon}</td></tr>'
    sections.append(_section("Overview", f"""
        <p><strong>ID:</strong> {project.id}</p>
        <p><strong>Idea:</strong> {_esc(project.idea)}</p>
        <table><thead><tr><th>Artifact</th><th>Ready</th></tr></thead><tbody>{status_rows}</tbody></table>
    """))

    b = project.business_analysis
    if b:
        competitors = "".join(f"<span class='badge'>{_esc(c)}</span> " for c in b.competitors)
        sections.append(_section("Business Analysis", f"""
            <h3>Market</h3><p>{_esc(b.market)}</p>
            <h3>Competitors</h3><p>{competitors}</p>
            <h3>Monetization</h3><p>{_esc(b.monetization)}</p>
        """))

    p = project.prd
    if p:
        features = "".join(f"<li>{_esc(f)}</li>" for f in p.features)
        stories = "".join(f"<li>{_esc(s)}</li>" for s in p.user_stories)
        roadmap = "".join(f"<li>{_esc(r)}</li>" for r in p.roadmap)
        sections.append(_section("Product Requirements", f"""
            <h3>Features</h3><ul>{features}</ul>
            <h3>User Stories</h3><ul>{stories}</ul>
            <h3>Roadmap</h3><ol>{roadmap}</ol>
        """))

    a = project.architecture
    if a:
        sections.append(_section("Architecture", f"""
            <div class="grid-2">
                <div class="card"><h3>Frontend</h3><p>{_esc(a.frontend)}</p></div>
                <div class="card"><h3>Backend</h3><p>{_esc(a.backend)}</p></div>
                <div class="card"><h3>Database</h3><p>{_esc(a.database)}</p></div>
                <div class="card"><h3>Infrastructure</h3><p>{_esc(a.infra)}</p></div>
            </div>
        """))

        mermaid = _build_architecture_mermaid(a)
        sections.append(_section("Architecture Diagram", f"""
            <div class="mermaid">{_esc(mermaid)}</div>
        """))

    t = project.tasks
    if t:
        epics = "".join(f"<li>{_esc(e)}</li>" for e in t.epics)
        issues = "".join(f"<li>{_esc(i)}</li>" for i in t.issues)
        sections.append(_section("Implementation Tasks", f"""
            <h3>Epics</h3><ul>{epics}</ul>
            <h3>Issues</h3><ol>{issues}</ol>
        """))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(project.idea)} — Project Report</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:system-ui,-apple-system,sans-serif; background:#0f172a; color:#e2e8f0; line-height:1.6; }}
.wrapper {{ max-width:960px; margin:0 auto; padding:2rem 1.5rem; }}
h1 {{ font-size:1.75rem; color:#f8fafc; margin-bottom:0.5rem; }}
h2 {{ font-size:1.25rem; color:#f8fafc; margin:1.5rem 0 0.75rem; border-bottom:1px solid #334155; padding-bottom:0.4rem; }}
h3 {{ font-size:1rem; color:#94a3b8; margin:1rem 0 0.4rem; }}
p {{ margin-bottom:0.75rem; }}
section {{ margin-bottom:1.5rem; }}
.card {{ background:#1e293b; border:1px solid #334155; border-radius:8px; padding:0.75rem; }}
.grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; }}
@media (max-width:600px) {{ .grid-2 {{ grid-template-columns:1fr; }} }}
table {{ width:100%; border-collapse:collapse; background:#1e293b; border-radius:8px; overflow:hidden; }}
th,td {{ padding:0.5rem 0.75rem; text-align:left; border-bottom:1px solid #334155; }}
th {{ background:#1e293b; color:#94a3b8; font-weight:600; }}
.yes {{ color:#4ade80; }} .no {{ color:#f87171; }}
ul,ol {{ padding-left:1.5rem; margin-bottom:0.75rem; }}
li {{ margin-bottom:0.3rem; }}
.badge {{ display:inline-block; background:#1e293b; border:1px solid #475569; border-radius:4px; padding:0.2rem 0.5rem; margin:0.2rem; font-size:0.85rem; }}
.mermaid {{ background:#1e293b; border:1px solid #334155; border-radius:8px; padding:1rem; font-family:monospace; white-space:pre; overflow-x:auto; font-size:0.85rem; }}
</style>
</head>
<body>
<div class="wrapper">
<h1>{_esc(project.idea)}</h1>
<p style="color:#64748b;font-size:0.875rem;">Generated by AI Project CTO</p>
{"".join(sections)}
</div>
</body>
</html>"""

    (out_dir / "report.html").write_text(html, encoding="utf-8")


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_architecture_mermaid(project: Project) -> str:
    """Generate a Mermaid.js architecture diagram from project data."""
    if not project.architecture:
        return "%% No architecture data available"
    return _build_architecture_mermaid(project.architecture)


def _build_architecture_mermaid(a) -> str:
    """Build Mermaid graph TD from Architecture model."""
    lines = ["graph TD"]
    lines.append(f"    User[\"User\"]")

    # Parse frontend info for tech names
    frontend_label = a.frontend.split(".")[0] if a.frontend and "." in a.frontend else (a.frontend[:50] if a.frontend else "Frontend")
    lines.append(f"    FE[\"{_esc_mermaid(frontend_label)}\"]")
    lines.append(f"    User -->|HTTP| FE")

    backend_label = a.backend.split(".")[0] if a.backend and "." in a.backend else (a.backend[:50] if a.backend else "Backend")
    lines.append(f"    BE[\"{_esc_mermaid(backend_label)}\"]")
    lines.append(f"    FE -->|API| BE")

    db_label = a.database.split(".")[0] if a.database and "." in a.database else (a.database[:50] if a.database else "Database")
    lines.append(f"    DB[\"{_esc_mermaid(db_label)}\"]")
    lines.append(f"    BE -->|SQL| DB")

    infra_label = a.infra.split(".")[0] if a.infra and "." in a.infra else (a.infra[:50] if a.infra else "Infrastructure")
    lines.append(f"    INFRA[\"{_esc_mermaid(infra_label)}\"]")
    lines.append(f"    BE -->|Deploy| INFRA")

    return "\n".join(lines)


def _esc_mermaid(text: str) -> str:
    return text.replace('"', "'").replace("(", "[").replace(")", "]")
