from __future__ import annotations

from hafermilch.core.models import LLMConfig
from hafermilch.llm.base import LLMProvider


class LLMProviderFactory:
    """Instantiates the correct LLMProvider from a LLMConfig."""

    @staticmethod
    def create(config: LLMConfig) -> LLMProvider:
        match config.provider:
            case "openai":
                from hafermilch.llm.openai_provider import OpenAIProvider

                return OpenAIProvider(
                    model=config.model,
                    temperature=config.temperature,
                    api_key=config.api_key,
                    base_url=config.base_url,
                    api_version=config.api_version,
                )
            case "gemini":
                from hafermilch.llm.gemini_provider import GeminiProvider

                return GeminiProvider(
                    model=config.model,
                    temperature=config.temperature,
                    api_key=config.api_key,
                )
            case "ollama":
                from hafermilch.llm.ollama_provider import OllamaProvider

                return OllamaProvider(
                    model=config.model,
                    temperature=config.temperature,
                    base_url=config.base_url,
                )
            case _:
                raise ValueError(f"Unknown LLM provider: '{config.provider}'")
