from pathlib import Path

from slugify import slugify

from packages.schemas import Architecture, BusinessAnalysis, ExportArtifact, PRD, Project, Tasks
from services.api.export import export_project_workspace


def _sample_project() -> Project:
    return Project(
        id="abc12345-0000-0000-0000-000000000001",
        idea="AI Resume SaaS",
        business_analysis=BusinessAnalysis(
            market="Large market",
            competitors=["Competitor A"],
            monetization="Subscription",
        ),
        prd=PRD(
            features=["Resume builder"],
            user_stories=["As a user I can upload my resume"],
            roadmap=["MVP", "Launch"],
        ),
        architecture=Architecture(
            frontend="Next.js",
            backend="FastAPI",
            database="PostgreSQL",
            infra="Vercel + Railway",
        ),
        tasks=Tasks(epics=["Auth epic"], issues=["Setup repo"]),
    )


def test_export_creates_markdown_files(tmp_path):
    project = _sample_project()
    out = export_project_workspace(project, tmp_path)
    assert out.is_dir()
    for name in [
        "00-overview.md",
        "01-business.md",
        "02-prd.md",
        "03-architecture.md",
        "04-roadmap.md",
        "05-tasks.md",
    ]:
        assert (out / name).exists()
    assert "AI Resume SaaS" in (out / "00-overview.md").read_text()


def test_export_appends_artifact_to_project(tmp_path):
    project = _sample_project()
    assert len(project.exports) == 0
    export_project_workspace(project, tmp_path)
    assert len(project.exports) == 1
    artifact = project.exports[0]
    assert artifact.format == "markdown"
    assert artifact.type == "workspace"
    assert len(artifact.files) == 6
    assert artifact.files[0].name == "00-overview.md"
    assert "AI Resume SaaS" in artifact.files[0].content


def test_slugify_fallback(tmp_path):
    project = Project(id="abc12345-0000-0000-0000-000000000001", idea="!!!")
    out = export_project_workspace(project, tmp_path)
    assert "abc12345" in str(out)
