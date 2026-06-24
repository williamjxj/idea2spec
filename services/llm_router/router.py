import json
import re
from typing import Any

import httpx

from services.llm_router.config import LLMSettings, TaskType, get_provider_config


class LLMRouterError(Exception):
    pass


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


class LLMRouter:
    def __init__(self, settings: LLMSettings | None = None):
        self.settings = settings or LLMSettings()

    async def complete_json(
        self,
        task: TaskType,
        system_prompt: str,
        user_prompt: str,
        *,
        retry_on_parse_error: bool = True,
    ) -> dict[str, Any]:
        raw = await self._chat(task, system_prompt, user_prompt)
        try:
            return _extract_json(raw)
        except json.JSONDecodeError as exc:
            if not retry_on_parse_error:
                raise LLMRouterError(f"Invalid JSON from LLM: {raw[:500]}") from exc
            fix_prompt = (
                f"Your previous response was not valid JSON. "
                f"Return ONLY valid JSON with no markdown fences.\n\nPrevious response:\n{raw}"
            )
            raw = await self._chat(task, system_prompt, fix_prompt, retry_on_parse_error=False)
            try:
                return _extract_json(raw)
            except json.JSONDecodeError as exc2:
                raise LLMRouterError(f"Invalid JSON after retry: {raw[:500]}") from exc2

    async def _chat(
        self,
        task: TaskType,
        system_prompt: str,
        user_prompt: str,
        *,
        retry_on_parse_error: bool = True,
    ) -> str:
        api_key, base_url, model, temperature = get_provider_config(task, self.settings)
        if not api_key:
            raise LLMRouterError(f"No API key configured for task {task.value}")

        base = base_url.rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        url = f"{base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code >= 400:
                raise LLMRouterError(
                    f"LLM request failed ({response.status_code}): {response.text[:500]}"
                )
            data = response.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMRouterError(f"Unexpected LLM response shape: {data}") from exc
