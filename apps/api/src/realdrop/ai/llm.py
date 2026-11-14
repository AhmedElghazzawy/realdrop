"""One client for every chat model we use: any OpenAI-compatible endpoint (local Ollama by
default, a free API tier in production), chosen by settings, never by code (ai-design.md).

Structured output only: callers pass a JSON schema and get a parsed object back. Temperature 0.
"""

import json
from dataclasses import dataclass
from typing import Any

import httpx

from realdrop.config import get_settings


class LLMError(RuntimeError):
    """The model answered with something that is not the JSON we asked for, or not at all."""


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int


class LLMClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.model = model or settings.llm_model_fast
        self._client = httpx.AsyncClient(
            base_url=(base_url or settings.llm_base_url).rstrip("/") + "/",
            headers={
                "Authorization": f"Bearer {api_key or settings.llm_api_key.get_secret_value()}"
            },
            timeout=timeout,
            transport=transport,
        )

    async def __aenter__(self) -> "LLMClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def json(
        self, messages: list[dict[str, str]], schema: dict[str, Any], *, name: str
    ) -> tuple[dict[str, Any], Usage]:
        """The model's answer as an object matching `schema` (validated by the caller)."""
        response = await self._client.post(
            "chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": name, "schema": schema, "strict": True},
                },
            },
        )
        if response.status_code != 200:
            raise LLMError(f"{response.status_code}: {response.text[:300]}")
        body = response.json()
        try:
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMError(f"unparseable answer: {str(body)[:300]}") from exc
        if not isinstance(parsed, dict):
            raise LLMError(f"expected an object, got {type(parsed).__name__}")
        usage = body.get("usage") or {}
        return parsed, Usage(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
