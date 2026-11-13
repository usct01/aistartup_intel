from __future__ import annotations

from aistartup_intel.agents.funding import FundingAnalyst, normalize_currency
from aistartup_intel.config.settings import Settings
from aistartup_intel.llm import LLMGateway
from aistartup_intel.models.agent_io import FundingAnalysisInput
from aistartup_intel.models.events import Claim, EvidenceSpan


def _claim(predicate: str, value, confidence: float, span: str) -> Claim:
    return Claim(predicate=predicate, value=value, confidence=confidence,
                 evidence=EvidenceSpan(text=span))


def test_normalize_currency():
    assert normalize_currency(100.0, "USD") == 100.0
    assert normalize_currency(100.0, "EUR") == 108.0
    assert normalize_currency(100.0, "XYZ") is None


async def test_round_normalization_and_lead():
    agent = FundingAnalyst(LLMGateway(settings=Settings(llm_offline=True)))
    claims = [
        _claim("raised_amount_usd", 25_000_000, 0.85, "raised $25M"),
        _claim("round_type", "series_a", 0.6, "Series A"),
        _claim("lead_investor", "Sequoia", 0.75, "led by Sequoia"),
        _claim("investor_mention", "Andreessen Horowitz", 0.55, "and Andreessen Horowitz"),
    ]
    result = await agent.handle(None, FundingAnalysisInput(claims=claims, company_ref="c1"))
    assert len(result.rounds) == 1
    round_ = result.rounds[0]
    assert round_.amount_usd == 25_000_000
    assert round_.round_type.value == "series_a"
    roles = {p.investor_name: p.role for p in round_.participants}
    assert roles["Sequoia"] == "lead"
    assert roles["Andreessen Horowitz"] == "participant"


async def test_conflicting_amounts_are_reported():
    agent = FundingAnalyst(LLMGateway(settings=Settings(llm_offline=True)))
    claims = [
        _claim("raised_amount_usd", 25_000_000, 0.5, "raised $25M"),
        _claim("raised_amount_usd", 30_000_000, 0.9, "raised $30M"),
    ]
    result = await agent.handle(None, FundingAnalysisInput(claims=claims, company_ref="c1"))
    assert result.conflicts
    assert result.rounds[0].amount_usd == 30_000_000  # highest confidence wins
