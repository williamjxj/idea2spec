"""Tests for ProjectStore using InMemoryStore (no Postgres required)."""

from services.api.store import InMemoryStore


async def test_create_and_retrieve():
    store = InMemoryStore()
    project = await store.create("AI Resume SaaS")
    assert project.id
    assert project.idea == "AI Resume SaaS"


async def test_get_nonexistent_returns_none():
    store = InMemoryStore()
    result = await store.get("nonexistent-id")
    assert result is None


async def test_save_updates_project():
    store = InMemoryStore()
    project = await store.create("Test idea")
    project.idea = "Updated idea"
    saved = await store.save(project)
    assert saved.idea == "Updated idea"
    retrieved = await store.get(project.id)
    assert retrieved is not None
    assert retrieved.idea == "Updated idea"


async def test_list_all():
    store = InMemoryStore()
    p1 = await store.create("Idea one")
    p2 = await store.create("Idea two")
    all_projects = await store.list_all()
    assert len(all_projects) == 2
    ids = [p.id for p in all_projects]
    assert p1.id in ids
    assert p2.id in ids


async def test_agent_artifacts_are_persisted():
    store = InMemoryStore()
    project = await store.create("Test")

    # Simulate running business agent
    from packages.schemas import BusinessAnalysis
    project.business_analysis = BusinessAnalysis(market="Big market", competitors=[], monetization="Ads")
    await store.save(project)

    retrieved = await store.get(project.id)
    assert retrieved is not None
    assert retrieved.business_analysis is not None
    assert retrieved.business_analysis.market == "Big market"


async def test_exports_list_is_accumulated():
    store = InMemoryStore()
    project = await store.create("Test exports")
    assert project.exports == []
