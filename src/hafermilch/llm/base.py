from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from hafermilch.core.exceptions import LLMProviderError


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
    async def complete(self, messages: list[Message]) -> str:
        """Send messages and return the raw text response."""

    async def complete_json(
        self,
        messages: list[Message],
        schema: type[BaseModel],
        max_retries: int = 2,
    ) -> BaseModel:
        """Send messages and parse the response as a Pydantic model.

        The last user message should instruct the model to reply with JSON
        conforming to the schema. We attempt to extract a JSON block even
        when the model wraps it in markdown fences.
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

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            raw = await self.complete(augmented)
            try:
                data = _extract_json(raw)
                return schema.model_validate(data)
            except Exception as exc:
                last_error = exc
                # Feed the error back so the model can self-correct
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
    # Strip ```json ... ``` or ``` ... ``` fences
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    # Fall back to finding the first { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])

    raise ValueError(f"No JSON object found in response: {text!r}")
