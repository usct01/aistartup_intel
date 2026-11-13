"""High-level persistence operations over the canonical store.

Agents do not write SQL directly; validated workflows call these functions, which
also maintain the append-only provenance ledger and run manifests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.domain import Company, Founder, FundingRound, TaxonomyTag
from ..models.events import Event, new_id
from ..models.scoring import Score
from .tables import (
    CompanyAliasRow,
    CompanyFounderRow,
    CompanyRow,
    CompanySignalRow,
    DocumentRow,
    EventRow,
    EvidenceSpanRow,
    FounderRow,
    FundingParticipantRow,
    FundingRoundRow,
    ProvenanceLedgerRow,
    RelationshipRow,
    ReviewQueueRow,
    RunManifestRow,
    SourceClaimRow,
    SubscriptionRow,
    TaxonomyTagRow,
    UserRow,
)


def _now() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- #
# Events
# --------------------------------------------------------------------------- #
def save_event(session: Session, event: Event) -> tuple[EventRow, bool]:
    """Persist a normalized event. Idempotent by event_id then content_hash.

    Returns (row, created).
    """
    existing = session.get(EventRow, event.event_id)
    if existing is not None:
        return existing, False
    if event.content_hash:
        dup = session.scalar(
            select(EventRow).where(EventRow.content_hash == event.content_hash).limit(1)
        )
        if dup is not None:
            return dup, False
    row = EventRow(
        event_id=event.event_id,
        source_id=event.source_id,
        source_tier=event.source_tier.value,
        kind=event.kind.value,
        observed_at=event.observed_at,
        occurred_at=event.occurred_at,
        title=event.title,
        payload=event.model_dump(mode="json"),
        raw_uri=event.raw_uri,
        content_hash=event.content_hash,
        processed=False,
    )
    session.add(row)
    session.flush()
    return row, True


def mark_event_processed(session: Session, event_id: str) -> None:
    row = session.get(EventRow, event_id)
    if row is not None:
        row.processed = True


def list_events(
    session: Session, *, kind: str | None = None, unprocessed_only: bool = False, limit: int = 100
) -> list[EventRow]:
    stmt = select(EventRow).order_by(EventRow.observed_at.desc()).limit(limit)
    if kind:
        stmt = stmt.where(EventRow.kind == kind)
    if unprocessed_only:
        stmt = stmt.where(EventRow.processed.is_(False))
    return list(session.scalars(stmt))


# --------------------------------------------------------------------------- #
# Documents & claims
# --------------------------------------------------------------------------- #
def add_document(
    session: Session,
    *,
    uri: str,
    url: str,
    source_id: str,
    content_hash: str,
    content_type: str = "text/html",
    http_status: int | None = None,
    from_cache: bool = False,
    raw_path: str | None = None,
) -> DocumentRow:
    existing = session.scalar(select(DocumentRow).where(DocumentRow.uri == uri))
    if existing is not None:
        return existing
    row = DocumentRow(
        id=new_id(),
        uri=uri,
        url=url,
        source_id=source_id,
        content_hash=content_hash,
        content_type=content_type,
        http_status=http_status,
        from_cache=from_cache,
        raw_path=raw_path,
    )
    session.add(row)
    session.flush()
    return row


def add_claim(
    session: Session,
    *,
    predicate: str,
    value: Any,
    confidence: float,
    evidence_text: str,
    document_uri: str | None = None,
    event_id: str | None = None,
    extracted_by: str | None = None,
    unit: str | None = None,
) -> SourceClaimRow:
    value_num = float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None
    row = SourceClaimRow(
        id=new_id(),
        predicate=predicate,
        value_text=None if value_num is not None else (str(value) if value is not None else None),
        value_num=value_num,
        unit=unit,
        confidence=confidence,
        event_id=event_id,
        extracted_by=extracted_by,
    )
    session.add(row)
    session.flush()
    session.add(
        EvidenceSpanRow(id=new_id(), claim_id=row.id, text=evidence_text, document_uri=document_uri)
    )
    session.flush()
    return row


# --------------------------------------------------------------------------- #
# Companies & funding
# --------------------------------------------------------------------------- #
def upsert_company(session: Session, company: Company) -> CompanyRow:
    row = session.get(CompanyRow, company.id)
    if row is None:
        row = CompanyRow(id=company.id, canonical_name=company.canonical_name)
        session.add(row)
    row.canonical_name = company.canonical_name
    row.url = company.url
    row.hq = company.hq
    row.description = company.description
    row.founded_year = company.founded_year
    row.employee_count = company.employee_count
    row.confidence = company.confidence
    row.is_new = company.is_new
    row.last_verified_at = company.last_verified_at
    session.flush()
    for alias in company.aliases:
        session.add(
            CompanyAliasRow(id=new_id(), company_id=row.id, alias=alias.alias, source_id=alias.source_id)
        )
    return row


def add_founder(session: Session, company_id: str, founder: Founder) -> FounderRow:
    row = session.get(FounderRow, founder.id)
    if row is None:
        row = FounderRow(
            id=founder.id,
            name=founder.name,
            role=founder.role,
            linkedin_url=founder.linkedin_url,
            prior_exits=founder.prior_exits,
            notable_employers=list(founder.notable_employers),
        )
        session.add(row)
        session.flush()
    link = session.get(CompanyFounderRow, (company_id, founder.id))
    if link is None:
        session.add(CompanyFounderRow(company_id=company_id, founder_id=founder.id))
    return row


def add_funding_round(session: Session, round_: FundingRound) -> FundingRoundRow:
    row = session.get(FundingRoundRow, round_.id)
    if row is None:
        row = FundingRoundRow(id=round_.id, company_id=round_.company_id)
        session.add(row)
    row.round_type = round_.round_type.value
    row.funding_type = round_.funding_type.value
    row.disclosure = round_.disclosure.value
    row.amount = round_.amount
    row.currency = round_.currency
    row.amount_usd = round_.amount_usd
    row.valuation_usd = round_.valuation_usd
    row.announced_on = round_.announced_on
    row.closed_on = round_.closed_on
    row.confidence = round_.confidence
    row.source_event_ids = list(round_.source_event_ids)
    row.correction_of = round_.correction_of
    session.flush()
    for p in round_.participants:
        session.add(
            FundingParticipantRow(
                id=new_id(),
                round_id=row.id,
                investor_id=p.investor_id,
                investor_name=p.investor_name,
                role=p.role,
            )
        )
    return row


def add_taxonomy_tags(session: Session, company_id: str, tags: list[TaxonomyTag]) -> int:
    added = 0
    for tag in tags:
        exists = session.scalar(
            select(TaxonomyTagRow).where(
                TaxonomyTagRow.company_id == company_id,
                TaxonomyTagRow.axis == tag.axis,
                TaxonomyTagRow.label == tag.label,
            )
        )
        if exists is None:
            session.add(
                TaxonomyTagRow(
                    id=new_id(),
                    company_id=company_id,
                    axis=tag.axis,
                    label=tag.label,
                    confidence=tag.confidence,
                )
            )
            added += 1
    session.flush()
    return added


def add_signal(
    session: Session,
    *,
    company_id: str,
    kind: str,
    summary: str,
    strength: float,
    source_event_ids: list[str] | None = None,
) -> CompanySignalRow:
    row = CompanySignalRow(
        id=new_id(),
        company_id=company_id,
        kind=kind,
        summary=summary,
        strength=strength,
        source_event_ids=source_event_ids or [],
    )
    session.add(row)
    session.flush()
    return row


def add_relationship(
    session: Session, *, kind: str, from_id: str, to_id: str, confidence: float
) -> RelationshipRow:
    row = RelationshipRow(id=new_id(), kind=kind, from_id=from_id, to_id=to_id, confidence=confidence)
    session.add(row)
    session.flush()
    return row


# --------------------------------------------------------------------------- #
# Queries
# --------------------------------------------------------------------------- #
def get_company(session: Session, company_id: str) -> CompanyRow | None:
    return session.get(CompanyRow, company_id)


def _threshold_sum_subquery() -> Any:
    return (
        select(
            FundingRoundRow.company_id.label("company_id"),
            func.coalesce(func.sum(FundingRoundRow.amount_usd), 0.0).label("total"),
        )
        .where(
            FundingRoundRow.disclosure == "disclosed",
            FundingRoundRow.amount_usd.is_not(None),
            FundingRoundRow.funding_type.in_(["equity", "convertible", "safe"]),
        )
        .group_by(FundingRoundRow.company_id)
        .subquery()
    )


def list_companies(
    session: Session,
    *,
    min_total_funding_usd: float | None = None,
    vertical: str | None = None,
    capability: str | None = None,
    buyer: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[tuple[CompanyRow, float]]:
    totals = _threshold_sum_subquery()
    stmt = (
        select(CompanyRow, func.coalesce(totals.c.total, 0.0))
        .outerjoin(totals, totals.c.company_id == CompanyRow.id)
        .order_by(func.coalesce(totals.c.total, 0.0).desc(), CompanyRow.canonical_name)
        .limit(limit)
        .offset(offset)
    )
    if min_total_funding_usd is not None:
        stmt = stmt.where(func.coalesce(totals.c.total, 0.0) > min_total_funding_usd)
    for axis, label in (("vertical", vertical), ("capability", capability), ("buyer", buyer)):
        if label:
            stmt = stmt.where(
                CompanyRow.id.in_(
                    select(TaxonomyTagRow.company_id).where(
                        TaxonomyTagRow.axis == axis, TaxonomyTagRow.label == label
                    )
                )
            )
    if q:
        stmt = stmt.where(CompanyRow.canonical_name.ilike(f"%{q}%"))
    return [(c, float(total)) for c, total in session.execute(stmt).all()]


def list_taxonomy(session: Session, *, axis: str | None = None) -> list[tuple[str, str, int]]:
    """Return (axis, label, company_count) tuples, most populated first."""
    stmt = (
        select(
            TaxonomyTagRow.axis,
            TaxonomyTagRow.label,
            func.count(func.distinct(TaxonomyTagRow.company_id)),
        )
        .group_by(TaxonomyTagRow.axis, TaxonomyTagRow.label)
        .order_by(func.count(func.distinct(TaxonomyTagRow.company_id)).desc(), TaxonomyTagRow.label)
    )
    if axis:
        stmt = stmt.where(TaxonomyTagRow.axis == axis)
    return [(a, label, int(count)) for a, label, count in session.execute(stmt).all()]


def company_total_disclosed_funding(session: Session, company_id: str) -> float:
    total = session.scalar(
        select(func.coalesce(func.sum(FundingRoundRow.amount_usd), 0.0)).where(
            FundingRoundRow.company_id == company_id,
            FundingRoundRow.disclosure == "disclosed",
            FundingRoundRow.amount_usd.is_not(None),
            FundingRoundRow.funding_type.in_(["equity", "convertible", "safe"]),
        )
    )
    return float(total or 0.0)


def list_funding_rounds(
    session: Session, *, company_id: str | None = None, min_amount_usd: float | None = None
) -> list[FundingRoundRow]:
    stmt = select(FundingRoundRow).order_by(FundingRoundRow.announced_on.desc().nullslast())
    if company_id:
        stmt = stmt.where(FundingRoundRow.company_id == company_id)
    if min_amount_usd is not None:
        stmt = stmt.where(FundingRoundRow.amount_usd > min_amount_usd)
    return list(session.scalars(stmt))


def count_companies(session: Session) -> int:
    return int(session.scalar(select(func.count(CompanyRow.id))) or 0)


# --------------------------------------------------------------------------- #
# Provenance ledger (append-only) & run manifests
# --------------------------------------------------------------------------- #
def append_ledger(
    session: Session,
    *,
    record_type: str,
    record_id: str,
    action: str,
    payload: dict[str, Any] | None = None,
    evidence: list[Any] | None = None,
    confidence: float | None = None,
    source_event_id: str | None = None,
    run_id: str | None = None,
    actor: str = "system",
) -> ProvenanceLedgerRow:
    row = ProvenanceLedgerRow(
        record_type=record_type,
        record_id=record_id,
        action=action,
        payload=payload or {},
        evidence=evidence or [],
        confidence=confidence,
        source_event_id=source_event_id,
        run_id=run_id,
        actor=actor,
    )
    session.add(row)
    session.flush()
    return row


def ledger_for(session: Session, record_id: str) -> list[ProvenanceLedgerRow]:
    return list(
        session.scalars(
            select(ProvenanceLedgerRow)
            .where(ProvenanceLedgerRow.record_id == record_id)
            .order_by(ProvenanceLedgerRow.seq)
        )
    )


def start_run(session: Session, *, input_ref: str | None = None, run_id: str | None = None) -> RunManifestRow:
    row = RunManifestRow(run_id=run_id or new_id(), input_ref=input_ref, status="running")
    session.add(row)
    session.flush()
    return row


def finish_run(
    session: Session,
    run_id: str,
    *,
    status: str = "completed",
    agents: list[Any] | None = None,
    models: list[Any] | None = None,
    total_tokens: int = 0,
    cost_usd: float = 0.0,
    decisions: dict[str, Any] | None = None,
) -> None:
    row = session.get(RunManifestRow, run_id)
    if row is None:
        return
    row.status = status
    row.finished_at = _now()
    if agents is not None:
        row.agents = agents
    if models is not None:
        row.models = models
    row.total_tokens = total_tokens
    row.cost_usd = cost_usd
    if decisions is not None:
        row.decisions = decisions
    session.flush()


def get_run(session: Session, run_id: str) -> RunManifestRow | None:
    return session.get(RunManifestRow, run_id)


# --------------------------------------------------------------------------- #
# Review queue
# --------------------------------------------------------------------------- #
def enqueue_review(
    session: Session,
    *,
    item_id: str,
    item_type: str,
    summary: str,
    confidence: float,
    reasons: list[str] | None = None,
    evidence: list[str] | None = None,
) -> ReviewQueueRow:
    row = ReviewQueueRow(
        id=new_id(),
        item_id=item_id,
        item_type=item_type,
        summary=summary,
        confidence=confidence,
        reasons=reasons or [],
        evidence=evidence or [],
        status="pending",
    )
    session.add(row)
    session.flush()
    return row


def list_reviews(
    session: Session, *, status: str | None = "pending", limit: int = 100
) -> list[ReviewQueueRow]:
    stmt = select(ReviewQueueRow).order_by(ReviewQueueRow.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(ReviewQueueRow.status == status)
    return list(session.scalars(stmt))


def resolve_review(
    session: Session, review_id: str, *, status: str, resolver: str, note: str | None = None
) -> ReviewQueueRow | None:
    row = session.get(ReviewQueueRow, review_id)
    if row is None:
        return None
    row.status = status
    row.resolver = resolver
    row.resolution_note = note
    row.resolved_at = _now()
    session.flush()
    return row


# --------------------------------------------------------------------------- #
# Scores (stored as signals-adjacent ledger entries for now)
# --------------------------------------------------------------------------- #
def record_score(session: Session, company_id: str, score: Score, *, run_id: str | None = None) -> None:
    append_ledger(
        session,
        record_type="company_score",
        record_id=company_id,
        action="score",
        payload=score.model_dump(mode="json"),
        confidence=score.value,
        run_id=run_id,
        actor="scoring-service",
    )


# --------------------------------------------------------------------------- #
# Subscribers & subscriptions
# --------------------------------------------------------------------------- #
def get_user_by_email(session: Session, email: str) -> UserRow | None:
    return session.scalar(select(UserRow).where(UserRow.email == email.lower()).limit(1))


def create_user(session: Session, *, email: str, name: str | None = None) -> tuple[UserRow, bool]:
    """Idempotently create a user by email. Returns (row, created)."""
    existing = get_user_by_email(session, email)
    if existing is not None:
        if name and not existing.name:
            existing.name = name
            session.flush()
        return existing, False
    row = UserRow(id=new_id(), email=email.lower(), name=name)
    session.add(row)
    session.flush()
    return row, True


def add_subscription(
    session: Session,
    *,
    user_id: str,
    verticals: list[str] | None = None,
    categories: list[str] | None = None,
    min_funding_usd: int = 0,
    active: bool = True,
) -> SubscriptionRow:
    row = SubscriptionRow(
        id=new_id(),
        user_id=user_id,
        verticals=list(verticals or []),
        categories=list(categories or []),
        min_funding_usd=min_funding_usd,
        active=active,
    )
    session.add(row)
    session.flush()
    return row


def get_subscription(session: Session, user_id: str) -> SubscriptionRow | None:
    return session.scalar(
        select(SubscriptionRow)
        .where(SubscriptionRow.user_id == user_id)
        .order_by(SubscriptionRow.created_at.desc())
        .limit(1)
    )


def list_subscribers(session: Session, *, limit: int = 200) -> list[tuple[UserRow, SubscriptionRow | None]]:
    users = list(session.scalars(select(UserRow).order_by(UserRow.created_at.desc()).limit(limit)))
    return [(u, get_subscription(session, u.id)) for u in users]
