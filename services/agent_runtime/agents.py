import json
from typing import Any

from packages.prompts import (
    ARCHITECT_SYSTEM,
    BUSINESS_SYSTEM,
    PLANNER_SYSTEM,
    PRODUCT_SYSTEM,
)
from packages.schemas import (
    Architecture,
    BusinessAnalysis,
    PRD,
    Project,
    Tasks,
)
from services.llm_router import LLMRouter, TaskType


def _context(project: Project) -> str:
    return json.dumps(project.model_dump(), indent=2, default=str)


async def run_business_agent(project: Project, router: LLMRouter) -> Project:
    data = await router.complete_json(
        TaskType.BUSINESS,
        BUSINESS_SYSTEM,
        f"Idea:\n{project.idea}",
    )
    project.business_analysis = BusinessAnalysis.model_validate(data)
    return project


async def run_product_agent(project: Project, router: LLMRouter) -> Project:
    data = await router.complete_json(
        TaskType.PRODUCT,
        PRODUCT_SYSTEM,
        f"Idea:\n{project.idea}\n\nCurrent project state:\n{_context(project)}",
    )
    project.prd = PRD.model_validate(data)
    return project


async def run_architect_agent(project: Project, router: LLMRouter) -> Project:
    data = await router.complete_json(
        TaskType.ARCHITECTURE,
        ARCHITECT_SYSTEM,
        f"Idea:\n{project.idea}\n\nCurrent project state:\n{_context(project)}",
    )
    project.architecture = Architecture.model_validate(data)
    return project


async def run_planner_agent(project: Project, router: LLMRouter) -> Project:
    data = await router.complete_json(
        TaskType.PLANNER,
        PLANNER_SYSTEM,
        f"Idea:\n{project.idea}\n\nCurrent project state:\n{_context(project)}",
    )
    project.tasks = Tasks.model_validate(data)
    return project


AGENT_RUNNERS: dict[str, Any] = {
    "business": run_business_agent,
    "product": run_product_agent,
    "architect": run_architect_agent,
    "planner": run_planner_agent,
}

STAGE_BY_AGENT = {
    "business": "business_complete",
    "product": "product_complete",
    "architect": "architect_complete",
    "planner": "planner_complete",
}
