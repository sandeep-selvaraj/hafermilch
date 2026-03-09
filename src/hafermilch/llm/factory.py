from __future__ import annotations

from hafermilch.core.models import LLMConfig
from hafermilch.llm.base import LLMProvider


class LLMProviderFactory:
    """Instantiates an LLMProvider from a LLMConfig via LiteLLM."""

    @staticmethod
    def create(config: LLMConfig) -> LLMProvider:
        from hafermilch.llm.litellm_provider import LiteLLMProvider

        return LiteLLMProvider(
            provider=config.provider,
            model=config.model,
            temperature=config.temperature,
            api_key=config.api_key,
            base_url=config.base_url,
            api_version=config.api_version,
        )
