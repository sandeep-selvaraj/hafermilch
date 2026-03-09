from __future__ import annotations

import base64
from typing import Any
from urllib.parse import urlparse

from hafermilch.core.exceptions import LLMProviderError
from hafermilch.core.settings import settings
from hafermilch.llm.base import LLMProvider, Message

try:
    from openai import APIError as OpenAIAPIError
    from openai import AsyncAzureOpenAI, AsyncOpenAI
    from openai import BadRequestError as OpenAIBadRequestError
except ImportError as exc:  # pragma: no cover
    raise ImportError("Install 'openai' to use the OpenAI provider.") from exc

import logging

logger = logging.getLogger(__name__)

# Parameters that some models (o1, o3, etc.) do not support
_UNSUPPORTED_PARAM_PHRASES = ("temperature", "max_tokens")

# Role name used by o1/o3 models instead of "system"
_SYSTEM_ROLE_ALIASES = ("unsupported value", "system")

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
            # Azure OpenAI: AsyncAzureOpenAI expects only the resource root
            # (https://your-resource.openai.azure.com/). Strip any path or
            # query string the user may have copied from the Azure portal.
            parsed = urlparse(base_url)
            azure_endpoint = f"{parsed.scheme}://{parsed.netloc}/"
            # If api_version wasn't set explicitly, fall back to the query
            # string from the URL (e.g. ?api-version=2024-05-01-preview)
            resolved_version = api_version or next(
                (
                    v
                    for k, v in (p.split("=", 1) for p in parsed.query.split("&") if "=" in p)
                    if k == "api-version"
                ),
                _AZURE_DEFAULT_API_VERSION,
            )
            self._client = AsyncAzureOpenAI(
                api_key=api_key or settings.azure_openai_api_key,
                azure_endpoint=azure_endpoint,
                api_version=resolved_version,
            )
        else:
            # Standard OpenAI
            self._client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)

    @property
    def supports_vision(self) -> bool:
        return self._model in _VISION_MODELS

    async def complete(self, messages: list[Message]) -> str:
        kwargs: dict[str, Any] = {"temperature": self._temperature}
        openai_messages = [_to_openai_message(m) for m in messages]
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except OpenAIBadRequestError as exc:
            error_body = str(exc).lower()
            logger.debug("Azure 400 error: %s", exc)

            # o1/o3 models reject `temperature` — retry without it
            if any(p in error_body for p in _UNSUPPORTED_PARAM_PHRASES):
                logger.debug("Retrying without unsupported parameter(s)")
                kwargs.pop("temperature", None)
                try:
                    response = await self._client.chat.completions.create(
                        model=self._model,
                        messages=openai_messages,
                        **kwargs,
                    )
                    return response.choices[0].message.content or ""
                except OpenAIBadRequestError as exc2:
                    error_body = str(exc2).lower()
                    logger.debug("Second 400 error: %s", exc2)
                    # Fall through to system-role handling below
                    exc = exc2

            # o1/o3 models reject role="system" — remap to role="developer"
            if "system" in error_body and "role" in error_body:
                logger.debug("Retrying with system→developer role remap")
                remapped = [
                    {**m, "role": "developer"} if m.get("role") == "system" else m
                    for m in openai_messages
                ]
                try:
                    response = await self._client.chat.completions.create(
                        model=self._model,
                        messages=remapped,
                        **kwargs,
                    )
                    return response.choices[0].message.content or ""
                except OpenAIAPIError as retry_exc:
                    raise LLMProviderError(f"OpenAI API error: {retry_exc}") from retry_exc

            raise LLMProviderError(f"OpenAI API error: {exc}") from exc
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
