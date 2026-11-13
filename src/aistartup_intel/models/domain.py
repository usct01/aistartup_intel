"""Canonical domain objects (companies, funding, investors, signals, taxonomy)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import DisclosureStatus, FundingType, RelationshipKind, RoundType
from .events import new_id


class CompanyAlias(BaseModel):
    alias: str
    source_id: str | None = None


class Investor(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    type: str = "vc"  # vc, corporate, angel, accelerator, government, other
    url: str | None = None
    aliases: list[str] = Field(default_factory=list)


class Founder(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    role: str | None = None
    linkedin_url: str | None = None
    prior_exits: int = 0
    notable_employers: list[str] = Field(default_factory=list)


class FundingParticipant(BaseModel):
    investor_id: str | None = None
    investor_name: str
    role: str = "participant"  # lead, participant, follow_on


class FundingRound(BaseModel):
    id: str = Field(default_factory=new_id)
    company_id: str
    round_type: RoundType = RoundType.OTHER
    funding_type: FundingType = FundingType.EQUITY
    disclosure: DisclosureStatus = DisclosureStatus.DISCLOSED
    amount: float | None = None
    currency: str = "USD"
    amount_usd: float | None = None
    valuation_usd: float | None = None
    announced_on: date | None = None
    closed_on: date | None = None
    participants: list[FundingParticipant] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_event_ids: list[str] = Field(default_factory=list)
    correction_of: str | None = None

    @property
    def counts_toward_threshold(self) -> bool:
        """Only disclosed, USD-normalized equity-ish amounts count (design rule)."""
        return (
            self.disclosure is DisclosureStatus.DISCLOSED
            and self.amount_usd is not None
            and self.funding_type
            in {FundingType.EQUITY, FundingType.CONVERTIBLE, FundingType.SAFE}
        )


class TaxonomyTag(BaseModel):
    axis: str  # vertical | capability | buyer | maturity
    label: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class CompanySignal(BaseModel):
    id: str = Field(default_factory=new_id)
    company_id: str
    kind: str  # funding_velocity, hiring, product, partnership, competitive, regulatory
    summary: str
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    occurred_at: datetime | None = None
    source_event_ids: list[str] = Field(default_factory=list)


class Company(BaseModel):
    id: str = Field(default_factory=new_id)
    canonical_name: str
    aliases: list[CompanyAlias] = Field(default_factory=list)
    url: str | None = None
    hq: str | None = None
    description: str | None = None
    founded_year: int | None = None
    taxonomy: list[TaxonomyTag] = Field(default_factory=list)
    founders: list[Founder] = Field(default_factory=list)
    investors: list[Investor] = Field(default_factory=list)
    funding_rounds: list[FundingRound] = Field(default_factory=list)
    employee_count: int | None = None
    last_verified_at: datetime | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    is_new: bool = False

    @property
    def total_disclosed_funding_usd(self) -> float:
        return sum(
            r.amount_usd or 0.0 for r in self.funding_rounds if r.counts_toward_threshold
        )

    def meets_funding_threshold(self, threshold: float) -> bool:
        return self.total_disclosed_funding_usd > threshold


class Relationship(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: RelationshipKind
    from_id: str
    to_id: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
