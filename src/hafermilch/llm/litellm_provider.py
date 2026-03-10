from __future__ import annotations

import base64
import contextlib
import logging
from typing import Any
from urllib.parse import urlparse

from hafermilch.core.exceptions import LLMProviderError
from hafermilch.core.models import TokenUsage
from hafermilch.llm.base import LLMProvider, Message

try:
    import litellm
    from litellm.exceptions import APIConnectionError, BadRequestError
except ImportError as exc:  # pragma: no cover
    raise ImportError("Install 'litellm' to use the LiteLLM provider.") from exc

logger = logging.getLogger(__name__)

# Suppress litellm's verbose success logging
litellm.success_callback = []
litellm.suppress_debug_info = True


def _build_model_string(provider: str, model: str) -> str:
    """Construct the LiteLLM model string from provider + model name.

    LiteLLM uses the format ``<provider>/<model>``, e.g.:
      openai/gpt-4o
      azure/my-deployment
      gemini/gemini-2.0-flash
      ollama/llava
      anthropic/claude-3-5-sonnet-20241022
    """
    # Already in LiteLLM format — pass through unchanged
    if "/" in provider or "/" in model:
        return model if "/" in model else f"{provider}/{model}"
    return f"{provider}/{model}"


def _extract_api_version(url: str) -> str | None:
    """Pull api-version from a query string if present."""
    parsed = urlparse(url)
    for part in parsed.query.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k == "api-version":
                return v
    return None


class LiteLLMProvider(LLMProvider):
    """Single LLM provider backed by LiteLLM — supports 100+ providers."""

    def __init__(
        self,
        provider: str,
        model: str,
        temperature: float,
        api_key: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self._model = _build_model_string(provider, model)
        self._temperature = temperature

        # Common kwargs forwarded to every litellm.acompletion call
        self._kwargs: dict[str, Any] = {}

        if api_key:
            self._kwargs["api_key"] = api_key

        if base_url:
            resolved_version = api_version or _extract_api_version(base_url)
            self._kwargs["api_base"] = base_url
            if resolved_version:
                self._kwargs["api_version"] = resolved_version
        elif api_version:
            self._kwargs["api_version"] = api_version

        logger.info(
            "LiteLLM config — model: %s | api_base: %s | api_version: %s",
            self._model,
            self._kwargs.get("api_base", "(none)"),
            self._kwargs.get("api_version", "(none)"),
        )

    @property
    def supports_vision(self) -> bool:
        try:
            return litellm.supports_vision(model=self._model)
        except Exception:
            return False

    async def complete(self, messages: list[Message]) -> tuple[str, TokenUsage | None]:
        litellm_messages = [_to_litellm_message(m) for m in messages]
        kwargs = {**self._kwargs, "temperature": self._temperature}

        try:
            response = await litellm.acompletion(
                model=self._model,
                messages=litellm_messages,
                **kwargs,
            )
            return response.choices[0].message.content or "", _extract_usage(response)

        except BadRequestError as exc:
            error_body = str(exc).lower()
            logger.debug("LiteLLM 400: %s", exc)

            # Some models (o1, o3) reject temperature — retry without it
            if "temperature" in error_body or "max_tokens" in error_body:
                kwargs.pop("temperature", None)
                logger.debug("Retrying without temperature")
                try:
                    response = await litellm.acompletion(
                        model=self._model,
                        messages=litellm_messages,
                        **kwargs,
                    )
                    return response.choices[0].message.content or "", _extract_usage(response)
                except Exception as retry_exc:
                    raise LLMProviderError(f"LLM error: {retry_exc}") from retry_exc

            raise LLMProviderError(f"LLM error: {exc}") from exc

        except APIConnectionError as exc:
            raise LLMProviderError(f"LLM connection error: {exc}") from exc

        except Exception as exc:
            raise LLMProviderError(f"LLM error: {exc}") from exc


def _extract_usage(response: Any) -> TokenUsage | None:
    """Pull token counts and cost from a LiteLLM response object."""
    try:
        u = response.usage
        cost: float | None = None
        with contextlib.suppress(Exception):
            cost = litellm.completion_cost(completion_response=response)
        return TokenUsage(
            prompt_tokens=u.prompt_tokens or 0,
            completion_tokens=u.completion_tokens or 0,
            total_tokens=u.total_tokens or 0,
            cost_usd=cost,
        )
    except Exception:
        return None


def _to_litellm_message(msg: Message) -> dict[str, Any]:
    if isinstance(msg.content, str):
        return {"role": msg.role, "content": msg.content}

    # Multimodal content
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
