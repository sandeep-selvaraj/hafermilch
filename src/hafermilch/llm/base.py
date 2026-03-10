from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from hafermilch.core.exceptions import LLMProviderError
from hafermilch.core.models import TokenUsage


class Message(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str | list[Any]  # list for multimodal (text + image)


class LLMProvider(ABC):
    """Abstract base for all LLM backends.

    Subclasses must implement `complete`. The `complete_json` helper is
    provided here so retry / extraction logic lives in one place.
    """

    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """True when the provider/model can accept image inputs."""

    @abstractmethod
    async def complete(self, messages: list[Message]) -> tuple[str, TokenUsage | None]:
        """Send messages and return the raw text response plus token usage."""

    async def complete_json(
        self,
        messages: list[Message],
        schema: type[BaseModel],
        max_retries: int = 2,
    ) -> tuple[BaseModel, TokenUsage | None]:
        """Send messages and parse the response as a Pydantic model.

        Returns the parsed model and accumulated token usage across all attempts.
        """
        schema_hint = _schema_hint(schema)
        augmented = messages + [
            Message(
                role="user",
                content=(
                    "Reply with a single JSON object that matches this schema "
                    f"(no extra text, no markdown fences):\n{schema_hint}"
                ),
            )
        ]

        accumulated_usage: TokenUsage | None = None
        last_error: Exception | None = None

        for _attempt in range(max_retries + 1):
            raw, usage = await self.complete(augmented)
            if usage is not None:
                accumulated_usage = (accumulated_usage + usage) if accumulated_usage else usage
            try:
                data = _extract_json(raw)
                return schema.model_validate(data), accumulated_usage
            except Exception as exc:
                last_error = exc
                augmented = augmented + [
                    Message(role="assistant", content=raw),
                    Message(
                        role="user",
                        content=(
                            f"That response was invalid. Error: {exc}. "
                            "Please reply with a corrected JSON object only."
                        ),
                    ),
                ]

        raise LLMProviderError(
            f"Failed to obtain valid JSON after {max_retries + 1} attempts: {last_error}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _schema_hint(schema: type[BaseModel]) -> str:
    """Return a compact JSON Schema string for the model."""
    return json.dumps(schema.model_json_schema(), indent=2)


def _extract_json(text: str) -> dict[str, Any]:
    """Extract the first JSON object from a string, stripping markdown fences."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])

    raise ValueError(f"No JSON object found in response: {text!r}")
