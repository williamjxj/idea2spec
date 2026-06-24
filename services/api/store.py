from uuid import uuid4

from packages.schemas import Project


class ProjectStore:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}

    def create(self, idea: str) -> Project:
        project = Project(id=str(uuid4()), idea=idea)
        self._projects[project.id] = project
        return project

    def get(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def save(self, project: Project) -> Project:
        self._projects[project.id] = project
        return project

    def list_all(self) -> list[Project]:
        return list(self._projects.values())


store = ProjectStore()
