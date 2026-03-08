"""Tests for LLM base — JSON extraction and complete_json retry logic."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from hafermilch.core.exceptions import LLMProviderError
from hafermilch.llm.base import LLMProvider, Message, _extract_json

# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------


def test_extract_json_plain():
    assert _extract_json('{"key": "value"}') == {"key": "value"}


def test_extract_json_strips_markdown_fence():
    text = '```json\n{"key": "value"}\n```'
    assert _extract_json(text) == {"key": "value"}


def test_extract_json_strips_plain_fence():
    text = '```\n{"key": "value"}\n```'
    assert _extract_json(text) == {"key": "value"}


def test_extract_json_embedded_in_prose():
    text = 'Here is the result: {"score": 9} — as requested.'
    assert _extract_json(text) == {"score": 9}


def test_extract_json_raises_when_no_json():
    with pytest.raises(ValueError, match="No JSON object found"):
        _extract_json("This has no JSON at all.")


# ---------------------------------------------------------------------------
# LLMProvider.complete_json — retry logic via a concrete stub
# ---------------------------------------------------------------------------


class _SimpleSchema(BaseModel):
    value: str


class _StubProvider(LLMProvider):
    """Minimal concrete provider that returns pre-set responses."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)

    @property
    def supports_vision(self) -> bool:
        return False

    async def complete(self, messages: list[Message]) -> str:
        return next(self._responses)


@pytest.mark.asyncio
async def test_complete_json_success_first_attempt():
    provider = _StubProvider(['{"value": "hello"}'])
    result = await provider.complete_json([], _SimpleSchema)
    assert result.value == "hello"


@pytest.mark.asyncio
async def test_complete_json_retries_on_bad_json():
    # First response is invalid, second is correct
    provider = _StubProvider(["not json at all", '{"value": "recovered"}'])
    result = await provider.complete_json([], _SimpleSchema, max_retries=1)
    assert result.value == "recovered"


@pytest.mark.asyncio
async def test_complete_json_raises_after_max_retries():
    provider = _StubProvider(["bad", "also bad", "still bad"])
    with pytest.raises(LLMProviderError, match="Failed to obtain valid JSON"):
        await provider.complete_json([], _SimpleSchema, max_retries=2)
