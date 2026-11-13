from __future__ import annotations

from datetime import date

from aistartup_intel.models.domain import Company, FundingRound
from aistartup_intel.models.enums import DisclosureStatus, FundingType, RoundType
from aistartup_intel.models.events import Claim, EvidenceSpan


def test_claim_predicate_is_normalized():
    c = Claim(predicate="Raised Amount USD", evidence=EvidenceSpan(text="x"))
    assert c.predicate == "raised_amount_usd"


def test_counts_toward_threshold_excludes_undisclosed_and_debt():
    disclosed = FundingRound(
        company_id="c1", amount_usd=12_000_000, disclosure=DisclosureStatus.DISCLOSED,
        funding_type=FundingType.EQUITY,
    )
    undisclosed = FundingRound(
        company_id="c1", amount_usd=9_000_000, disclosure=DisclosureStatus.UNDISCLOSED,
    )
    debt = FundingRound(
        company_id="c1", amount_usd=5_000_000, funding_type=FundingType.DEBT,
        round_type=RoundType.DEBT,
    )
    company = Company(canonical_name="Acme", funding_rounds=[disclosed, undisclosed, debt])
    assert company.total_disclosed_funding_usd == 12_000_000


def test_funding_threshold_is_strictly_greater_than():
    exactly = Company(
        canonical_name="Acme",
        funding_rounds=[FundingRound(company_id="c", amount_usd=10_000_000,
                                     announced_on=date(2026, 1, 1))],
    )
    assert exactly.meets_funding_threshold(10_000_000) is False
    assert exactly.meets_funding_threshold(9_999_999) is True
