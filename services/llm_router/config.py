from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class TaskType(str, Enum):
    BUSINESS = "business"
    PRODUCT = "product"
    ARCHITECTURE = "architecture"
    PLANNER = "planner"
    FALLBACK = "fallback"


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-pro"

    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "kimi-k2.5"

    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com/v1"
    minimax_model: str = "MiniMax-M2.5"


def get_provider_config(task: TaskType, settings: LLMSettings) -> tuple[str, str, str, float]:
    """Return (api_key, base_url, model, temperature) for the given task type."""
    routing = {
        TaskType.BUSINESS: ("kimi", settings.kimi_api_key, settings.kimi_base_url, settings.kimi_model, 1.0),
        TaskType.PRODUCT: ("deepseek", settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model, 0.3),
        TaskType.ARCHITECTURE: ("deepseek", settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model, 0.3),
        TaskType.PLANNER: ("minimax", settings.minimax_api_key, settings.minimax_base_url, settings.minimax_model, 0.3),
        TaskType.FALLBACK: ("deepseek", settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model, 0.3),
    }
    provider, api_key, base_url, model, temperature = routing[task]
    if not api_key:
        _, api_key, base_url, model, temperature = routing[TaskType.FALLBACK]
    return api_key, base_url, model, temperature
