from services.llm_router.config import LLMSettings, TaskType, get_provider_config


def test_routing_business_uses_kimi():
    settings = LLMSettings(
        kimi_api_key="kimi-key",
        kimi_base_url="https://kimi.example/v1",
        kimi_model="kimi-k2.5",
        deepseek_api_key="ds-key",
        deepseek_base_url="https://ds.example",
        deepseek_model="deepseek-v4-pro",
    )
    api_key, base_url, model, _ = get_provider_config(TaskType.BUSINESS, settings)
    assert model == "kimi-k2.5"
    assert "kimi" in base_url


def test_routing_planner_uses_minimax():
    settings = LLMSettings(
        minimax_api_key="mm-key",
        minimax_base_url="https://mm.example/v1",
        minimax_model="MiniMax-M2.5",
        deepseek_api_key="ds-key",
    )
    _, _, model, _ = get_provider_config(TaskType.PLANNER, settings)
    assert model == "MiniMax-M2.5"


def test_fallback_when_primary_missing():
    settings = LLMSettings(
        kimi_api_key="",
        deepseek_api_key="ds-key",
        deepseek_base_url="https://ds.example",
        deepseek_model="deepseek-v4-pro",
    )
    _, _, model, _ = get_provider_config(TaskType.BUSINESS, settings)
    assert model == "deepseek-v4-pro"
