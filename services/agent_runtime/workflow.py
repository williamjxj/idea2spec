from typing import Literal

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from packages.schemas import Project
from services.agent_runtime.agents import (
    STAGE_BY_AGENT,
    AGENT_RUNNERS,
    run_architect_agent,
    run_business_agent,
    run_planner_agent,
    run_product_agent,
)
from services.llm_router import LLMRouter


class GraphState(TypedDict):
    idea: str
    project: Project
    stage: str


def build_pipeline_graph(router: LLMRouter | None = None):
    """Full linear pipeline: business → product → architect → planner."""
    llm = router or LLMRouter()

    async def business(state: GraphState) -> GraphState:
        project = await run_business_agent(state["project"], llm)
        return {"idea": state["idea"], "project": project, "stage": "business_complete"}

    async def product(state: GraphState) -> GraphState:
        project = await run_product_agent(state["project"], llm)
        return {"idea": state["idea"], "project": project, "stage": "product_complete"}

    async def architect(state: GraphState) -> GraphState:
        project = await run_architect_agent(state["project"], llm)
        return {"idea": state["idea"], "project": project, "stage": "architect_complete"}

    async def planner(state: GraphState) -> GraphState:
        project = await run_planner_agent(state["project"], llm)
        return {"idea": state["idea"], "project": project, "stage": "planner_complete"}

    graph = StateGraph(GraphState)
    graph.add_node("business", business)
    graph.add_node("product", product)
    graph.add_node("architect", architect)
    graph.add_node("planner", planner)
    graph.add_edge(START, "business")
    graph.add_edge("business", "product")
    graph.add_edge("product", "architect")
    graph.add_edge("architect", "planner")
    graph.add_edge("planner", END)
    return graph.compile()


async def run_single_agent(
    agent: Literal["business", "product", "architect", "planner"],
    project: Project,
    router: LLMRouter | None = None,
) -> Project:
    llm = router or LLMRouter()
    runner = AGENT_RUNNERS[agent]
    updated = await runner(project, llm)
    return updated
