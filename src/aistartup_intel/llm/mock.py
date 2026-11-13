"""Deterministic offline model used when no network/API key is available.

It returns canned text supplied by the caller. Agents pair this with their own
deterministic logic so the full pipeline is testable and reproducible offline.
"""

from __future__ import annotations

from collections.abc import Callable

from .base import LLMResponse


class MockLLM:
    def __init__(self, responder: Callable[[str, str, str], str] | None = None) -> None:
        self._responder = responder

    async def complete(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        text = self._responder(model, system, user) if self._responder else ""
        return LLMResponse(text=text, model=f"mock:{model}", raw={"offline": True})
