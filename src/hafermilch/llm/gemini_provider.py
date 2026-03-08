from __future__ import annotations

from hafermilch.core.exceptions import LLMProviderError
from hafermilch.core.settings import settings
from hafermilch.llm.base import LLMProvider, Message

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError as exc:  # pragma: no cover
    raise ImportError("Install 'google-genai' to use the Gemini provider.") from exc

_VISION_MODELS = {
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
}


class GeminiProvider(LLMProvider):
    def __init__(self, model: str, temperature: float, api_key: str | None) -> None:
        self._model_name = model
        self._temperature = temperature
        self._client = genai.Client(api_key=api_key or settings.google_api_key)

    @property
    def supports_vision(self) -> bool:
        return self._model_name in _VISION_MODELS

    async def complete(self, messages: list[Message]) -> str:
        try:
            system_instruction, contents = _split_messages(messages)

            config = genai_types.GenerateContentConfig(
                temperature=self._temperature,
                system_instruction=system_instruction,
            )

            response = await self._client.aio.models.generate_content(
                model=self._model_name,
                contents=contents,
                config=config,
            )
            return response.text or ""
        except Exception as exc:
            raise LLMProviderError(f"Gemini API error: {exc}") from exc


def _split_messages(
    messages: list[Message],
) -> tuple[str | None, list[genai_types.Content]]:
    """Convert hafermilch messages into the google-genai Contents format."""
    system_instruction: str | None = None
    contents: list[genai_types.Content] = []

    for msg in messages:
        if msg.role == "system":
            system_instruction = msg.content if isinstance(msg.content, str) else ""
            continue

        role = "user" if msg.role == "user" else "model"
        parts = _to_genai_parts(msg.content)
        contents.append(genai_types.Content(role=role, parts=parts))

    return system_instruction, contents


def _to_genai_parts(content: str | list) -> list[genai_types.Part]:
    if isinstance(content, str):
        return [genai_types.Part.from_text(text=content)]

    parts: list[genai_types.Part] = []
    for item in content:
        if item["type"] == "text":
            parts.append(genai_types.Part.from_text(text=item["text"]))
        elif item["type"] == "image":
            parts.append(genai_types.Part.from_bytes(data=item["data"], mime_type="image/png"))
    return parts
