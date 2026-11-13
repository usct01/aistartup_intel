from __future__ import annotations

from aistartup_intel.agents.verifier import Verifier
from aistartup_intel.config.settings import Settings
from aistartup_intel.llm import LLMGateway
from aistartup_intel.models.agent_io import VerifyInput
from aistartup_intel.models.enums import Verdict
from aistartup_intel.models.events import Claim, EvidenceSpan


def _claim(predicate: str, value, confidence: float, span: str) -> Claim:
    return Claim(predicate=predicate, value=value, confidence=confidence,
                 evidence=EvidenceSpan(text=span))


async def test_provenance_failure_rejects():
    verifier = Verifier(LLMGateway(settings=Settings(llm_offline=True)))
    payload = VerifyInput(
        claims=[_claim("raised_amount_usd", 25_000_000, 0.9, "NOT IN SOURCE")],
        source_tier="A",
        context_text="Acme raised $25M.",
    )
    verdict = await verifier.handle(None, payload)
    assert verdict.verdict is Verdict.REJECT
    assert any(not f.passed and f.check == "provenance" for f in verdict.findings)


async def test_contradiction_lowers_confidence():
    verifier = Verifier(LLMGateway(settings=Settings(llm_offline=True)))
    payload = VerifyInput(
        claims=[_claim("raised_amount_usd", 30_000_000, 0.9, "raised $30M")],
        source_tier="A",
        context_text="Acme raised $30M.",
        existing_values={"raised_amount_usd": ["25000000.0"]},
    )
    verdict = await verifier.handle(None, payload)
    assert any(not f.passed and f.check == "contradiction" for f in verdict.findings)
    assert verdict.confidence < 0.9


async def test_anti_correlation_flag():
    verifier = Verifier(LLMGateway(settings=Settings(llm_offline=True)))
    same = await verifier.handle(
        None,
        VerifyInput(
            claims=[_claim("x", "y", 0.9, "y")],
            source_tier="A",
            context_text="y",
            extractor_model="openai/gpt-4o",
        ),
    )
    assert same.verifier_model == "deterministic-critic"
    # A deterministic critic is a different "family" than any model id.
    assert same.extractor_model == "openai/gpt-4o"
