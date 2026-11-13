from __future__ import annotations

from aistartup_intel.agents.entity_resolution import EntityResolver, normalize_name, similarity
from aistartup_intel.config.settings import Settings
from aistartup_intel.llm import LLMGateway
from aistartup_intel.models.agent_io import EntityRef, EntityResolutionInput


def test_normalize_strips_suffixes():
    assert normalize_name("Acme AI, Inc.") == "acme"


def test_similarity_identical_and_distinct():
    assert similarity("Acme AI", "Acme") >= 0.8
    assert similarity("Acme AI", "Globex") < 0.3


async def test_resolver_merges_and_reviews():
    resolver = EntityResolver(LLMGateway(settings=Settings(llm_offline=True)))
    payload = EntityResolutionInput(
        existing=[EntityRef(id="e1", name="Acme AI Inc"),
                  EntityRef(id="e2", name="Totally Different Corp")],
        incoming=[EntityRef(id="i1", name="Acme AI")],
    )
    result = await resolver.handle(None, payload)
    assert result.decisions
    best = max(result.decisions, key=lambda d: d.score)
    assert best.right_id == "e1"
    assert best.decision == "merge"
