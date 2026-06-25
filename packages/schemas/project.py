from datetime import datetime

from pydantic import BaseModel, Field


class BusinessAnalysis(BaseModel):
    market: str = ""
    competitors: list[str] = Field(default_factory=list)
    monetization: str = ""


class PRD(BaseModel):
    features: list[str] = Field(default_factory=list)
    user_stories: list[str] = Field(default_factory=list)
    roadmap: list[str] = Field(default_factory=list)


class Architecture(BaseModel):
    frontend: str = ""
    backend: str = ""
    database: str = ""
    infra: str = ""


class Tasks(BaseModel):
    epics: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class ExportFile(BaseModel):
    name: str
    content: str


class ExportArtifact(BaseModel):
    format: str          # "markdown" | "pdf" | "html" | "mermaid"
    type: str            # "workspace" | "business-report" | "architecture-diagram"
    files: list[ExportFile]
    created_at: datetime


class Project(BaseModel):
    id: str
    idea: str
    business_analysis: BusinessAnalysis | None = None
    prd: PRD | None = None
    architecture: Architecture | None = None
    tasks: Tasks | None = None
    exports: list[ExportArtifact] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProjectState(BaseModel):
    idea: str
    project: Project
    stage: str = "created"
