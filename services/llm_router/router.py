import json
import re
from typing import Any

import httpx

from services.llm_router.config import LLMSettings, TaskType, get_provider_config


class LLMRouterError(Exception):
    pass


def _extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from LLM output.

    Handles common failure modes:
      - Text preamble before the JSON (e.g. "好的，这是分析结果：\\n{...}")
      - Text postamble after the JSON (e.g. "{...}\\n希望这个分析对您有帮助！")
      - Markdown code fences with or without ``json`` tag
      - ``<think>`` reasoning blocks (MiniMax, DeepSeek)
      - Plain JSON with surrounding whitespace

    Strategy:
      1. Strip ``<think>`` blocks
      2. Try markdown fence extraction
      3. Try brace-delimited extraction (first ``{`` to last ``}``)
      4. Fall back to raw parse
    """
    original = text
    text = text.strip()

    # 1. Strip reasoning tags some models (MiniMax, DeepSeek) add
    text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()

    # 2. Try markdown code fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()

    # 3. Primary parse attempt — handles clean JSON and fence-extracted JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 4. Brace-delimited extraction — handles preambles and postambles.
    #    Find the first '{' and the last '}', extract everything between.
    #    This is the standard approach for LLM JSON extraction
    #    (cf. LangChain's parse_json_markdown, llama.cpp's json-schema-mode).
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace : last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 5. Last resort — try the original raw text (after think-stripping)
    #    in case the model returned valid JSON with unusual delimiters
    raise json.JSONDecodeError(
        f"Could not extract valid JSON from: {original[:300]}...",
        original,
        0,
    )


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
                "Your last output was NOT valid JSON and could not be parsed. "
                "You MUST output ONLY a JSON object — start with {, end with }. "
                "NO preamble, NO explanation, NO markdown, NO text outside the braces."
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

        async with httpx.AsyncClient(timeout=300.0) as client:
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
