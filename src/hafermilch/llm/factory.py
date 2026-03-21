from __future__ import annotations

from hafermilch.core.models import LLMConfig
from hafermilch.llm.base import LLMProvider


def create_llm_provider(config: LLMConfig) -> LLMProvider:
    """Instantiate an LLMProvider from a LLMConfig via LiteLLM."""
    from hafermilch.llm.litellm_provider import LiteLLMProvider

    return LiteLLMProvider(
        provider=config.provider,
        model=config.model,
        temperature=config.temperature,
        api_key=config.api_key,
        base_url=config.base_url,
        api_version=config.api_version,
    )
