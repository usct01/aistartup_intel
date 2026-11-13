"""OpenRouter client (OpenAI-compatible) with retry and cost accounting."""

from __future__ import annotations

import time

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ..config.settings import get_settings
from .base import LLMResponse
from .pricing import estimate_cost


class OpenRouterClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        key = api_key or settings.openrouter_api_key
        if not key:
            raise ValueError("OPENROUTER_API_KEY (AISI_OPENROUTER_API_KEY) is required")
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=key,
            base_url=base_url or settings.openrouter_base_url,
            timeout=settings.llm_timeout_seconds,
            default_headers={
                "HTTP-Referer": settings.openrouter_referer,
                "X-Title": settings.openrouter_title,
            },
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=20),
        reraise=True,
    )
    async def complete(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        started = time.perf_counter()
        resp = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        pt = usage.prompt_tokens if usage else 0
        ct = usage.completion_tokens if usage else 0
        return LLMResponse(
            text=text,
            model=model,
            prompt_tokens=pt,
            completion_tokens=ct,
            cost_usd=estimate_cost(model, pt, ct),
            latency_ms=latency_ms,
        )
