from __future__ import annotations

import base64
from typing import Any

from hafermilch.core.exceptions import LLMProviderError
from hafermilch.core.settings import settings
from hafermilch.llm.base import LLMProvider, Message

try:
    from openai import AsyncAzureOpenAI, AsyncOpenAI
    from openai import APIError as OpenAIAPIError
except ImportError as exc:  # pragma: no cover
    raise ImportError("Install 'openai' to use the OpenAI provider.") from exc

# Models that support image inputs (applies to both OpenAI and Azure deployments)
_VISION_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4-vision-preview"}

# Default Azure API version used when none is specified in the persona config
_AZURE_DEFAULT_API_VERSION = "2024-02-01"


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        model: str,
        temperature: float,
        api_key: str | None,
        base_url: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self._model = model
        self._temperature = temperature

        if base_url:
            # Azure OpenAI: base_url is the Azure endpoint
            self._client = AsyncAzureOpenAI(
                api_key=api_key or settings.azure_openai_api_key,
                azure_endpoint=base_url,
                api_version=api_version or _AZURE_DEFAULT_API_VERSION,
            )
        else:
            # Standard OpenAI
            self._client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)

    @property
    def supports_vision(self) -> bool:
        return self._model in _VISION_MODELS

    async def complete(self, messages: list[Message]) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                temperature=self._temperature,
                messages=[_to_openai_message(m) for m in messages],
            )
            return response.choices[0].message.content or ""
        except OpenAIAPIError as exc:
            raise LLMProviderError(f"OpenAI API error: {exc}") from exc


def _to_openai_message(msg: Message) -> dict[str, Any]:
    if isinstance(msg.content, str):
        return {"role": msg.role, "content": msg.content}

    # Multimodal: content is a list of {"type": ..., ...} parts
    parts: list[dict[str, Any]] = []
    for part in msg.content:
        if part["type"] == "text":
            parts.append({"type": "text", "text": part["text"]})
        elif part["type"] == "image":
            b64 = base64.b64encode(part["data"]).decode()
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )
    return {"role": msg.role, "content": parts}
