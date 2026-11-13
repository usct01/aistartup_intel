from __future__ import annotations

import pytest

from aistartup_intel.config.settings import Settings
from aistartup_intel.llm.base import LLMResponse, SchemaValidationError
from aistartup_intel.llm.gateway import LLMGateway, extract_json
from aistartup_intel.models.agent_io import ResearchPlan


class FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls = 0

    async def complete(self, *, model, system, user, temperature=0.0, max_tokens=None):
        self.calls += 1
        text = self.responses.pop(0) if self.responses else "{}"
        return LLMResponse(text=text, model=model, prompt_tokens=10, completion_tokens=5)


def _settings(**kw) -> Settings:
    return Settings(llm_offline=False, openrouter_api_key="test", **kw)


def test_extract_json_from_fenced_block():
    assert extract_json('prefix ```json\n{"a": 1}\n``` suffix') == {"a": 1}


def test_extract_json_from_plain_object():
    assert extract_json('noise {"a": 2} tail') == {"a": 2}


def test_extract_json_raises_without_object():
    with pytest.raises(SchemaValidationError):
        extract_json("no json here")


async def test_offline_requires_mock_factory():
    gw = LLMGateway(settings=Settings(llm_offline=True))
    with pytest.raises(SchemaValidationError):
        await gw.complete_structured(
            role="planner", system="s", user="u", schema=ResearchPlan, agent="planner"
        )


async def test_offline_uses_mock_factory():
    gw = LLMGateway(settings=Settings(llm_offline=True))
    result = await gw.complete_structured(
        role="planner",
        system="s",
        user="u",
        schema=ResearchPlan,
        agent="planner",
        mock=lambda: {"tasks": []},
    )
    assert isinstance(result.data, ResearchPlan)


async def test_online_repairs_invalid_json_then_succeeds():
    client = FakeClient(
        [
            "not json",
            '{"tasks": [{"task_id": "t", "vertical": "legal", "query": "q", "rationale": "r"}]}',
        ]
    )
    gw = LLMGateway(client=client, settings=_settings())
    result = await gw.complete_structured(
        role="planner", system="s", user="u", schema=ResearchPlan, agent="planner"
    )
    assert result.attempts == 2
    assert result.data.tasks[0].vertical == "legal"


async def test_online_exhausts_fallbacks_and_raises():
    client = FakeClient(["bad"] * 8)
    gw = LLMGateway(client=client, settings=_settings())
    with pytest.raises(SchemaValidationError):
        await gw.complete_structured(
            role="planner", system="s", user="u", schema=ResearchPlan, agent="planner"
        )
