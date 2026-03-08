from __future__ import annotations

from hafermilch.core.exceptions import LLMProviderError
from hafermilch.core.settings import settings
from hafermilch.llm.base import LLMProvider, Message

try:
    import ollama
except ImportError as exc:  # pragma: no cover
    raise ImportError("Install 'ollama' to use the Ollama provider.") from exc

# Commonly available vision-capable models served through Ollama
_VISION_MODELS = {"llava", "llava:13b", "llava:34b", "llava-phi3", "moondream"}


class OllamaProvider(LLMProvider):
    def __init__(self, model: str, temperature: float, base_url: str | None = None) -> None:
        self._model = model
        self._temperature = temperature
        # Priority: base_url from persona YAML → OLLAMA_HOST env var → default
        self._client = ollama.AsyncClient(host=base_url or settings.ollama_host)

    @property
    def supports_vision(self) -> bool:
        return self._model.split(":")[0] in _VISION_MODELS

    async def complete(self, messages: list[Message]) -> str:
        try:
            response = await self._client.chat(
                model=self._model,
                messages=[_to_ollama_message(m) for m in messages],
                options={"temperature": self._temperature},
            )
            return response["message"]["content"]
        except Exception as exc:
            raise LLMProviderError(f"Ollama error: {exc}") from exc


def _to_ollama_message(msg: Message) -> dict:
    if isinstance(msg.content, str):
        return {"role": msg.role, "content": msg.content}

    text_parts = []
    images = []
    for part in msg.content:
        if part["type"] == "text":
            text_parts.append(part["text"])
        elif part["type"] == "image":
            images.append(part["data"])  # raw bytes

    result: dict = {"role": msg.role, "content": " ".join(text_parts)}
    if images:
        result["images"] = images
    return result
