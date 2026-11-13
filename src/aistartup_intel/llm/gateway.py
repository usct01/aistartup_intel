"""The single LLM entry point used by every agent.

Responsibilities: task-based model routing, JSON-schema enforcement with repair
and fallback, cost/token accounting, and per-agent budget guards. In offline mode
it delegates to a deterministic mock and callers supply a ``mock`` factory.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from ..config.settings import Settings, get_settings
from .base import LLMClient, LLMError, LLMResponse, SchemaValidationError
from .mock import MockLLM
from .openrouter import OpenRouterClient

TModel = TypeVar("TModel", bound=BaseModel)

_ROLE_TO_SETTING = {
    "planner": "model_planner",
    "extractor": "model_extractor",
    "verifier": "model_verifier",
    "classifier_bulk": "model_classifier_bulk",
    "classifier_hard": "model_classifier_hard",
    "analyst": "model_analyst",
    "editor": "model_editor",
    "evaluator": "model_evaluator",
}

# Ordered fallbacks used when the primary model fails validation repeatedly.
_FALLBACKS: dict[str, list[str]] = {
    "planner": ["model_classifier_hard"],
    "extractor": ["model_classifier_hard"],
    "verifier": ["model_planner"],
    "classifier_hard": ["model_extractor"],
    "analyst": ["model_editor"],
    "editor": ["model_analyst"],
}

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of a model response."""
    match = _JSON_BLOCK.search(text)
    candidate = match.group(1) if match else text
    candidate = candidate.strip()
    if not candidate:
        raise SchemaValidationError("empty model response")
    try:
        parsed: dict[str, Any] = json.loads(candidate)
        return parsed
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(candidate[start : end + 1])
            return parsed
        raise SchemaValidationError("no JSON object found in response") from None


@dataclass
class CostTracker:
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    by_agent: dict[str, dict[str, float]] = field(default_factory=dict)

    def record(self, agent: str, model: str, prompt: int, completion: int, cost: float) -> None:
        self.total_tokens += prompt + completion
        self.total_cost_usd += cost
        bucket = self.by_agent.setdefault(agent, {"tokens": 0.0, "cost": 0.0, "calls": 0.0})
        bucket["tokens"] += prompt + completion
        bucket["cost"] += cost
        bucket["calls"] += 1


@dataclass
class StructuredResult:
    data: BaseModel
    model: str
    attempts: int
    cost_usd: float
    total_tokens: int
    response: LLMResponse | None = None


class LLMGateway:
    def __init__(
        self,
        *,
        client: LLMClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.tracker = CostTracker()
        self.client = client or self._build_client()

    def _build_client(self) -> LLMClient:
        if self.settings.llm_offline or not self.settings.openrouter_api_key:
            return MockLLM()
        return OpenRouterClient()

    @property
    def online(self) -> bool:
        return not isinstance(self.client, MockLLM)

    def model_for(self, role: str) -> str:
        attr = _ROLE_TO_SETTING.get(role)
        if attr is None:
            raise LLMError(f"unknown model role: {role}")
        return str(getattr(self.settings, attr))

    def fallback_models(self, role: str) -> list[str]:
        names = [self.model_for(role)]
        for attr in _FALLBACKS.get(role, []):
            names.append(str(getattr(self.settings, attr)))
        seen: list[str] = []
        for n in names:
            if n not in seen:
                seen.append(n)
        return seen

    def _budget_exceeded(self, agent: str) -> bool:
        if self.tracker.total_cost_usd >= self.settings.daily_spend_cap_usd:
            return True
        bucket = self.tracker.by_agent.get(agent, {})
        return bucket.get("tokens", 0) >= self.settings.per_agent_token_budget

    async def complete_text(
        self,
        *,
        role: str,
        system: str,
        user: str,
        agent: str = "unknown",
        temperature: float = 0.0,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        chosen = model or self.model_for(role)
        resp = await self.client.complete(
            model=chosen, system=system, user=user, temperature=temperature, max_tokens=max_tokens
        )
        self.tracker.record(agent, chosen, resp.prompt_tokens, resp.completion_tokens, resp.cost_usd)
        return resp

    async def complete_structured(
        self,
        *,
        role: str,
        system: str,
        user: str,
        schema: type[TModel],
        agent: str = "unknown",
        mock: Callable[[], Any] | None = None,
        temperature: float = 0.0,
    ) -> StructuredResult:
        if self._budget_exceeded(agent):
            raise LLMError(f"budget exceeded for agent '{agent}'")

        if not self.online:
            if mock is None:
                raise SchemaValidationError(
                    f"offline mode requires a mock factory for {schema.__name__}"
                )
            value = mock()
            data = value if isinstance(value, schema) else schema.model_validate(value)
            return StructuredResult(data=data, model="mock", attempts=1, cost_usd=0.0, total_tokens=0)

        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        instruction = (
            f"{system}\n\nReturn ONLY a JSON object matching this JSON Schema:\n{schema_json}"
        )
        attempts = 0
        last_error: Exception | None = None
        for model in self.fallback_models(role):
            prompt = user
            for _ in range(2):  # initial + one repair
                attempts += 1
                resp = await self.client.complete(
                    model=model, system=instruction, user=prompt, temperature=temperature
                )
                self.tracker.record(
                    agent, model, resp.prompt_tokens, resp.completion_tokens, resp.cost_usd
                )
                try:
                    payload = extract_json(resp.text)
                    data = schema.model_validate(payload)
                    return StructuredResult(
                        data=data,
                        model=model,
                        attempts=attempts,
                        cost_usd=resp.cost_usd,
                        total_tokens=resp.total_tokens,
                        response=resp,
                    )
                except (SchemaValidationError, ValidationError) as exc:
                    last_error = exc
                    prompt = (
                        f"{user}\n\nYour previous response was invalid: {exc}. "
                        "Return corrected JSON only."
                    )
        raise SchemaValidationError(
            f"schema validation failed for {schema.__name__} after {attempts} attempts: {last_error}"
        )
