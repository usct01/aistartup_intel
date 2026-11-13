"""Funding Analyst agent: normalizes rounds, currencies, dates, and conflicts."""

from __future__ import annotations

from datetime import date

from ..models.agent_io import FundingAnalysis, FundingAnalysisInput
from ..models.domain import FundingParticipant, FundingRound
from ..models.enums import DisclosureStatus, FundingType, RoundType
from .base import Agent, PipelineContext

# Minimal FX table; production should use a dated rate source.
_FX_TO_USD = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CAD": 0.73, "INR": 0.012}

_ROUND_MAP = {r.value: r for r in RoundType}


def normalize_currency(amount: float, currency: str) -> float | None:
    rate = _FX_TO_USD.get(currency.upper())
    return None if rate is None else amount * rate


class FundingAnalyst(Agent[FundingAnalysisInput, FundingAnalysis]):
    name = "funding-analyst"
    model_role = "analyst"
    description = "Normalizes round types, currency/date distinctions, totals, conflicts."

    async def handle(self, ctx: PipelineContext, payload: FundingAnalysisInput) -> FundingAnalysis:
        conflicts: list[str] = []
        amounts = [c for c in payload.claims if c.predicate == "raised_amount_usd"]
        if not amounts:
            return FundingAnalysis()
        if len(amounts) > 1:
            values = {c.value for c in amounts}
            if len(values) > 1:
                conflicts.append(f"conflicting funding amounts: {sorted(map(str, values))}")
        chosen = max(amounts, key=lambda c: c.confidence)

        amount = float(chosen.value) if chosen.value is not None else None
        currency = "USD"
        amount_usd = normalize_currency(amount, currency) if amount is not None else None

        round_type = RoundType.OTHER
        for c in payload.claims:
            if c.predicate == "round_type" and isinstance(c.value, str):
                round_type = _ROUND_MAP.get(c.value, RoundType.OTHER)
                break

        announced = None
        for c in payload.claims:
            if c.predicate == "announced_on" and isinstance(c.value, str):
                try:
                    announced = date.fromisoformat(c.value)
                except ValueError:
                    announced = None
                break

        participants: list[FundingParticipant] = []
        lead = next((c.value for c in payload.claims if c.predicate == "lead_investor"), None)
        if lead and isinstance(lead, str):
            participants.append(FundingParticipant(investor_name=lead, role="lead"))
        for c in payload.claims:
            if c.predicate == "investor_mention" and isinstance(c.value, str) and c.value != lead:
                participants.append(FundingParticipant(investor_name=c.value, role="participant"))

        funding_type = FundingType.EQUITY
        if round_type in {RoundType.DEBT}:
            funding_type = FundingType.DEBT
        elif round_type in {RoundType.GRANT}:
            funding_type = FundingType.GRANT

        round_ = FundingRound(
            company_id=payload.company_ref or "unresolved",
            round_type=round_type,
            funding_type=funding_type,
            disclosure=DisclosureStatus.DISCLOSED if amount_usd is not None else DisclosureStatus.UNDISCLOSED,
            amount=amount,
            currency=currency,
            amount_usd=amount_usd,
            announced_on=announced,
            participants=participants,
            confidence=chosen.confidence,
        )
        return FundingAnalysis(rounds=[round_], conflicts=conflicts)
