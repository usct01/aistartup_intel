"""SQLAlchemy ORM tables for the canonical knowledge base.

Portable across SQLite (dev) and PostgreSQL (prod). Nested payloads that are not
queried structurally use JSON. The provenance ledger and run manifests are
append-only by convention (no UPDATE/DELETE through the repository).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[Any]: JSON}


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


# --------------------------------------------------------------------------- #
# Companies & people
# --------------------------------------------------------------------------- #
class CompanyRow(TimestampMixin, Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(512), index=True)
    url: Mapped[str | None] = mapped_column(String(1024))
    hq: Mapped[str | None] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)
    founded_year: Mapped[int | None] = mapped_column(Integer)
    employee_count: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    aliases: Mapped[list[CompanyAliasRow]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    funding_rounds: Mapped[list[FundingRoundRow]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    taxonomy_tags: Mapped[list[TaxonomyTagRow]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    signals: Mapped[list[CompanySignalRow]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class CompanyAliasRow(TimestampMixin, Base):
    __tablename__ = "company_aliases"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    alias: Mapped[str] = mapped_column(String(512))
    source_id: Mapped[str | None] = mapped_column(String(128))
    company: Mapped[CompanyRow] = relationship(back_populates="aliases")


class FounderRow(TimestampMixin, Base):
    __tablename__ = "founders"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), index=True)
    role: Mapped[str | None] = mapped_column(String(256))
    linkedin_url: Mapped[str | None] = mapped_column(String(1024))
    prior_exits: Mapped[int] = mapped_column(Integer, default=0)
    notable_employers: Mapped[list[Any]] = mapped_column(JSON, default=list)


class CompanyFounderRow(Base):
    __tablename__ = "company_founders"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), primary_key=True)
    founder_id: Mapped[str] = mapped_column(ForeignKey("founders.id"), primary_key=True)


class InvestorRow(TimestampMixin, Base):
    __tablename__ = "investors"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), index=True)
    type: Mapped[str] = mapped_column(String(64), default="vc")
    url: Mapped[str | None] = mapped_column(String(1024))
    aliases: Mapped[list[Any]] = mapped_column(JSON, default=list)


class RelationshipRow(TimestampMixin, Base):
    __tablename__ = "relationships"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    from_id: Mapped[str] = mapped_column(String(32), index=True)
    to_id: Mapped[str] = mapped_column(String(32), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)


# --------------------------------------------------------------------------- #
# Funding
# --------------------------------------------------------------------------- #
class FundingRoundRow(TimestampMixin, Base):
    __tablename__ = "funding_rounds"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    round_type: Mapped[str] = mapped_column(String(32), default="other")
    funding_type: Mapped[str] = mapped_column(String(32), default="equity")
    disclosure: Mapped[str] = mapped_column(String(32), default="disclosed")
    amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    amount_usd: Mapped[float | None] = mapped_column(Float, index=True)
    valuation_usd: Mapped[float | None] = mapped_column(Float)
    announced_on: Mapped[date | None] = mapped_column(Date)
    closed_on: Mapped[date | None] = mapped_column(Date)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    source_event_ids: Mapped[list[Any]] = mapped_column(JSON, default=list)
    correction_of: Mapped[str | None] = mapped_column(String(32))
    company: Mapped[CompanyRow] = relationship(back_populates="funding_rounds")
    participants: Mapped[list[FundingParticipantRow]] = relationship(
        back_populates="round", cascade="all, delete-orphan"
    )


class FundingParticipantRow(TimestampMixin, Base):
    __tablename__ = "funding_participants"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    round_id: Mapped[str] = mapped_column(ForeignKey("funding_rounds.id"), index=True)
    investor_id: Mapped[str | None] = mapped_column(String(32))
    investor_name: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(32), default="participant")
    round: Mapped[FundingRoundRow] = relationship(back_populates="participants")


# --------------------------------------------------------------------------- #
# Taxonomy & signals
# --------------------------------------------------------------------------- #
class TaxonomyTagRow(TimestampMixin, Base):
    __tablename__ = "taxonomy_tags"
    __table_args__ = (UniqueConstraint("company_id", "axis", "label", name="uq_tag"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    axis: Mapped[str] = mapped_column(String(32), index=True)
    label: Mapped[str] = mapped_column(String(256), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    company: Mapped[CompanyRow] = relationship(back_populates="taxonomy_tags")


class CompanySignalRow(TimestampMixin, Base):
    __tablename__ = "company_signals"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(Text)
    strength: Mapped[float] = mapped_column(Float, default=0.5)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_event_ids: Mapped[list[Any]] = mapped_column(JSON, default=list)
    company: Mapped[CompanyRow] = relationship(back_populates="signals")


# --------------------------------------------------------------------------- #
# Documents, claims, evidence, events
# --------------------------------------------------------------------------- #
class DocumentRow(TimestampMixin, Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    uri: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(1024))
    source_id: Mapped[str] = mapped_column(String(128), index=True)
    content_type: Mapped[str] = mapped_column(String(128), default="text/html")
    content_hash: Mapped[str] = mapped_column(String(80), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    http_status: Mapped[int | None] = mapped_column(Integer)
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_path: Mapped[str | None] = mapped_column(String(1024))


class EventRow(Base):
    __tablename__ = "events"
    event_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(128), index=True)
    source_tier: Mapped[str] = mapped_column(String(4))
    kind: Mapped[str] = mapped_column(String(32), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    title: Mapped[str | None] = mapped_column(String(1024))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    raw_uri: Mapped[str | None] = mapped_column(String(1024))
    content_hash: Mapped[str | None] = mapped_column(String(80), index=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class SourceClaimRow(TimestampMixin, Base):
    __tablename__ = "source_claims"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    event_id: Mapped[str | None] = mapped_column(String(32), index=True)
    predicate: Mapped[str] = mapped_column(String(128), index=True)
    value_text: Mapped[str | None] = mapped_column(Text)
    value_num: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    extracted_by: Mapped[str | None] = mapped_column(String(128))


class EvidenceSpanRow(Base):
    __tablename__ = "evidence_spans"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("source_claims.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    start: Mapped[int | None] = mapped_column(Integer)
    end: Mapped[int | None] = mapped_column(Integer)
    document_uri: Mapped[str | None] = mapped_column(String(1024))


# --------------------------------------------------------------------------- #
# Crawl registry & runs
# --------------------------------------------------------------------------- #
class CrawlSourceRow(TimestampMixin, Base):
    __tablename__ = "crawl_sources"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    base_url: Mapped[str | None] = mapped_column(String(1024))
    source_type: Mapped[str] = mapped_column(String(64), default="web")
    tier: Mapped[str] = mapped_column(String(4), default="B")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    health: Mapped[str] = mapped_column(String(32), default="unknown")
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    legal_note: Mapped[str | None] = mapped_column(Text)


class CrawlRunRow(Base):
    __tablename__ = "crawl_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(128), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="running")
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    items_new: Mapped[int] = mapped_column(Integer, default=0)
    diagnostics: Mapped[list[Any]] = mapped_column(JSON, default=list)


# --------------------------------------------------------------------------- #
# Provenance ledger & run manifests (append-only)
# --------------------------------------------------------------------------- #
class ProvenanceLedgerRow(Base):
    __tablename__ = "provenance_ledger"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_type: Mapped[str] = mapped_column(String(64), index=True)
    record_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    evidence: Mapped[list[Any]] = mapped_column(JSON, default=list)
    confidence: Mapped[float | None] = mapped_column(Float)
    source_event_id: Mapped[str | None] = mapped_column(String(32), index=True)
    run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    actor: Mapped[str] = mapped_column(String(128), default="system")
    written_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RunManifestRow(Base):
    __tablename__ = "run_manifests"
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="running")
    input_ref: Mapped[str | None] = mapped_column(String(256))
    agents: Mapped[list[Any]] = mapped_column(JSON, default=list)
    models: Mapped[list[Any]] = mapped_column(JSON, default=list)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    decisions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    replayable: Mapped[bool] = mapped_column(Boolean, default=True)


# --------------------------------------------------------------------------- #
# Human review queue
# --------------------------------------------------------------------------- #
class ReviewQueueRow(TimestampMixin, Base):
    __tablename__ = "review_queue"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    item_id: Mapped[str] = mapped_column(String(64), index=True)
    item_type: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reasons: Mapped[list[Any]] = mapped_column(JSON, default=list)
    evidence: Mapped[list[Any]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolver: Mapped[str | None] = mapped_column(String(128))
    resolution_note: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------------------- #
# Users, subscriptions, watchlists, newsletter
# --------------------------------------------------------------------------- #
class UserRow(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    email: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(256))


class SubscriptionRow(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    verticals: Mapped[list[Any]] = mapped_column(JSON, default=list)
    categories: Mapped[list[Any]] = mapped_column(JSON, default=list)
    min_funding_usd: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class WatchlistRow(TimestampMixin, Base):
    __tablename__ = "watchlists"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(256))


class WatchlistCompanyRow(Base):
    __tablename__ = "watchlist_companies"
    watchlist_id: Mapped[str] = mapped_column(ForeignKey("watchlists.id"), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), primary_key=True)


class NewsletterEditionRow(TimestampMixin, Base):
    __tablename__ = "newsletter_editions"
    __table_args__ = (
        UniqueConstraint("user_id", "edition_date", name="uq_edition_user_date"),
    )
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    edition_date: Mapped[date] = mapped_column(Date)
    subject: Mapped[str] = mapped_column(String(512))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
