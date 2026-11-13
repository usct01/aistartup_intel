"""Enumerations shared across the domain, agents, and storage layers."""

from __future__ import annotations

from enum import StrEnum


class SourceTier(StrEnum):
    """Reliability/latency tier used for source-confidence weighting."""

    PRIMARY = "A"  # official filings, registries, company/VC pages
    COMMUNITY = "B"  # community/fast: HN, PH, X, GitHub, arXiv
    AGGREGATOR = "C"  # paid/curated aggregators: Crunchbase, PitchBook


class EventKind(StrEnum):
    LAUNCH = "launch"
    FUNDING = "funding"
    FOUNDER_MOVE = "founder_move"
    OSS_RELEASE = "oss_release"
    HIRING = "hiring"
    REGULATORY = "regulatory"
    PRODUCT = "product"
    PARTNERSHIP = "partnership"
    CUSTOMER_WIN = "customer_win"
    RESEARCH = "research"


class FundingType(StrEnum):
    EQUITY = "equity"
    DEBT = "debt"
    GRANT = "grant"
    CONVERTIBLE = "convertible"
    SAFE = "safe"
    OTHER = "other"


class RoundType(StrEnum):
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    SERIES_D = "series_d"
    SERIES_E = "series_e"
    GROWTH = "growth"
    DEBT = "debt"
    GRANT = "grant"
    IPO = "ipo"
    UNDISCLOSED = "undisclosed"
    OTHER = "other"


class DisclosureStatus(StrEnum):
    DISCLOSED = "disclosed"
    UNDISCLOSED = "undisclosed"
    ESTIMATED = "estimated"


class Verdict(StrEnum):
    PUBLISH = "publish"
    QUARANTINE = "quarantine"
    REJECT = "reject"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EntityType(StrEnum):
    COMPANY = "company"
    PERSON = "person"
    INVESTOR = "investor"
    PRODUCT = "product"


class RelationshipKind(StrEnum):
    FOUNDED_BY = "founded_by"
    INVESTED_IN = "invested_in"
    EMPLOYED_BY = "employed_by"
    SUBSIDIARY_OF = "subsidiary_of"
    ALIAS_OF = "alias_of"
    COMPETES_WITH = "competes_with"
