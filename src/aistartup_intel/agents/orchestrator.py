"""Orchestrator: routes events through the typed agent DAG and persists results.

Order for a signal: extract -> resolve company -> funding analysis -> taxonomy ->
signals -> verify -> (score) -> publish or human review. Every step is recorded in
a run manifest; canonical writes go through the repository (which maintains the
append-only provenance ledger).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.agent_io import (
    ClassifyInput,
    ExtractRequest,
    FundingAnalysisInput,
    NewsletterDraft,
    NewsletterInput,
    SignalInput,
    VerifyInput,
)
from ..models.domain import Company, FundingRound
from ..models.enums import EventKind, Verdict
from ..models.events import Claim, Event
from ..models.scoring import Score, ScoreFeatures
from ..scoring.service import MomentumScorer
from ..store import repository as repo
from ..store.tables import CompanyAliasRow, CompanyRow, FundingRoundRow
from .base import AgentRecord, PipelineContext
from .entity_resolution import EntityResolver
from .extraction import DocumentExtractor
from .funding import FundingAnalyst
from .newsletter import NewsletterEditor
from .review import HumanReviewQueue
from .signals import SignalAnalyst
from .taxonomy import TaxonomyClassifier
from .verifier import Verifier

_TIER_SCORE = {"A": 1.0, "B": 0.7, "C": 0.85}


@dataclass
class EventOutcome:
    event_id: str
    run_id: str
    company_id: str | None
    verdict: Verdict | None
    confidence: float
    published: bool = False
    review_id: str | None = None
    score: float | None = None
    conflicts: list[str] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)


class Orchestrator:
    def __init__(self, ctx: PipelineContext) -> None:
        self.ctx = ctx
        self.llm = ctx.llm
        self.extractor = DocumentExtractor(self.llm)
        self.resolver = EntityResolver(self.llm)
        self.funding = FundingAnalyst(self.llm)
        self.taxonomy = TaxonomyClassifier(self.llm)
        self.signals = SignalAnalyst(self.llm)
        self.verifier = Verifier(self.llm)
        self.review = HumanReviewQueue()
        self.editor = NewsletterEditor(self.llm)
        self.scorer = MomentumScorer()

    async def process_events(self, events: Iterable[Event]) -> list[EventOutcome]:
        outcomes: list[EventOutcome] = []
        for event in events:
            outcomes.append(await self.process_event(event))
        return outcomes

    async def process_event(self, event: Event) -> EventOutcome:
        session = self.ctx.session
        assert session is not None, "orchestrator requires a session"
        row, _created = repo.save_event(session, event)
        run = repo.start_run(session, input_ref=event.event_id)
        manifest_agents: list[dict[str, Any]] = []

        outcome = EventOutcome(
            event_id=event.event_id,
            run_id=run.run_id,
            company_id=None,
            verdict=None,
            confidence=0.0,
        )

        try:
            text = _event_text(event)
            extraction = await self.extractor.handle(
                self.ctx,
                ExtractRequest(
                    text=text,
                    source_id=event.source_id,
                    source_tier=event.source_tier.value,
                    url=event.provenance.url,
                ),
            )
            manifest_agents.append(AgentRecord(self.extractor.name, self.extractor.model).__dict__)

            claims = _dedupe_claims([*event.claims, *extraction.claims])

            company_name = _company_name(claims, extraction.company_mentions, event)
            company_row, is_new = self._resolve_company(
                session, company_name, url=event.provenance.url
            )
            outcome.company_id = company_row.id
            if is_new:
                repo.append_ledger(
                    session,
                    record_type="company",
                    record_id=company_row.id,
                    action="created",
                    payload={"canonical_name": company_row.canonical_name},
                    source_event_id=event.event_id,
                    run_id=run.run_id,
                )

            # Funding is analyzed but not persisted until it passes verification.
            analysis_rounds: list[FundingRound] = []
            if event.kind is EventKind.FUNDING:
                analysis = await self.funding.handle(
                    self.ctx,
                    FundingAnalysisInput(
                        claims=claims, company_ref=company_row.id, context_text=text
                    ),
                )
                outcome.conflicts.extend(analysis.conflicts)
                analysis_rounds = analysis.rounds
                manifest_agents.append(AgentRecord(self.funding.name, self.funding.model).__dict__)

            current_total = repo.company_total_disclosed_funding(session, company_row.id)
            projected_total = current_total + sum(
                r.amount_usd or 0.0 for r in analysis_rounds if r.counts_toward_threshold
            )
            classify = await self.taxonomy.handle(
                self.ctx,
                ClassifyInput(
                    company_name=company_row.canonical_name,
                    text=text or (company_row.description or ""),
                    total_funding_usd=projected_total,
                ),
            )
            repo.add_taxonomy_tags(session, company_row.id, classify.tags)
            manifest_agents.append(AgentRecord(self.taxonomy.name, self.taxonomy.model).__dict__)

            sig = await self.signals.handle(
                self.ctx,
                SignalInput(
                    company_name=company_row.canonical_name,
                    event_kinds=[event.kind.value],
                    funding_rounds=analysis_rounds,
                    text=text,
                ),
            )
            for s in sig.signals:
                repo.add_signal(
                    session,
                    company_id=company_row.id,
                    kind=str(s.get("kind", "unknown")),
                    summary=str(s.get("summary", "")),
                    strength=float(s.get("strength", 0.5)),
                    source_event_ids=[event.event_id],
                )

            existing_values = self._existing_values(session, company_row.id)
            verdict = await self.verifier.handle(
                self.ctx,
                VerifyInput(
                    claims=claims,
                    source_tier=event.source_tier.value,
                    source_id=event.source_id,
                    context_text=text or None,
                    existing_values=existing_values,
                    extractor_model=extraction.model_used,
                ),
            )
            manifest_agents.append(AgentRecord(self.verifier.name, self.verifier.model).__dict__)
            outcome.verdict = verdict.verdict
            outcome.confidence = verdict.confidence

            if verdict.verdict is Verdict.PUBLISH:
                outcome.published = True
                for round_ in analysis_rounds:
                    repo.add_funding_round(session, round_)
                    repo.append_ledger(
                        session,
                        record_type="funding_round",
                        record_id=round_.id,
                        action="created",
                        payload=round_.model_dump(mode="json"),
                        evidence=[
                            c.evidence.text
                            for c in claims
                            if c.predicate == "raised_amount_usd"
                        ],
                        confidence=round_.confidence,
                        source_event_id=event.event_id,
                        run_id=run.run_id,
                    )
                score = self._score(session, company_row, event)
                outcome.score = score.value
                repo.record_score(session, company_row.id, score, run_id=run.run_id)

            if self.review.should_review(verdict):
                packet = self.review.build_packet(
                    item_id=company_row.id,
                    item_type="company",
                    summary=f"{event.kind.value}: {company_name}",
                    verdict=verdict,
                    evidence=[c.evidence.text for c in claims][:5],
                )
                review_row = repo.enqueue_review(
                    session,
                    item_id=packet.item_id,
                    item_type=packet.item_type,
                    summary=packet.summary,
                    confidence=packet.confidence,
                    reasons=packet.reasons,
                    evidence=packet.evidence,
                )
                outcome.review_id = review_row.id

            repo.append_ledger(
                session,
                record_type="verification",
                record_id=event.event_id,
                action=verdict.verdict.value,
                payload={"confidence": verdict.confidence, "reasons": verdict.reasons},
                confidence=verdict.confidence,
                source_event_id=event.event_id,
                run_id=run.run_id,
                actor=self.verifier.name,
            )
            repo.mark_event_processed(session, event.event_id)

            repo.finish_run(
                session,
                run.run_id,
                status="completed",
                agents=manifest_agents,
                decisions={"verdict": verdict.verdict.value, "confidence": verdict.confidence},
                cost_usd=self.llm.tracker.total_cost_usd,
                total_tokens=self.llm.tracker.total_tokens,
            )
        except Exception as exc:  # noqa: BLE001 - record failure, keep batch alive
            outcome.diagnostics.append(f"pipeline error: {exc}")
            repo.finish_run(session, run.run_id, status="failed", agents=manifest_agents)
        return outcome

    # ------------------------------------------------------------------ #
    def _resolve_company(
        self, session: Session, name: str, *, url: str | None = None
    ) -> tuple[CompanyRow, bool]:
        existing = session.scalar(
            select(CompanyRow).where(CompanyRow.canonical_name == name).limit(1)
        )
        if existing is not None:
            if url and not existing.url:
                existing.url = url
                session.flush()
            return existing, False
        alias = session.scalar(select(CompanyAliasRow).where(CompanyAliasRow.alias == name).limit(1))
        if alias is not None:
            parent = session.get(CompanyRow, alias.company_id)
            if parent is not None:
                return parent, False
        company = Company(canonical_name=name, url=url, is_new=True)
        row = repo.upsert_company(session, company)
        return row, True

    def _existing_values(self, session: Session, company_id: str) -> dict[str, list[str]]:
        amounts = session.scalars(
            select(FundingRoundRow.amount_usd).where(FundingRoundRow.company_id == company_id)
        ).all()
        values = {"raised_amount_usd": [str(a) for a in amounts if a is not None]}
        return values

    def _score(self, session: Session, company: CompanyRow, event: Event) -> Score:
        total = repo.company_total_disclosed_funding(session, company.id)
        latest_stage = session.scalar(
            select(FundingRoundRow.round_type)
            .where(FundingRoundRow.company_id == company.id)
            .order_by(FundingRoundRow.announced_on.desc().nullslast())
            .limit(1)
        )
        features = ScoreFeatures(
            total_disclosed_funding_usd=total,
            latest_round_stage=latest_stage,
            rounds_count=1,
            source_tier_score=_TIER_SCORE.get(event.source_tier.value, 0.7),
            corroboration_count=1,
        )
        return self.scorer.score(features, evidence={"funding": [event.provenance.url]})


def _event_text(event: Event) -> str:
    parts: list[str] = []
    if event.title:
        parts.append(event.title)
    parts.extend(c.evidence.text for c in event.claims if c.evidence.text)
    return " ".join(dict.fromkeys(parts))


def _company_name(claims: Sequence[Claim], mentions: Sequence[object], event: Event) -> str:
    for c in claims:
        if c.predicate == "company_name" and isinstance(c.value, str) and c.value:
            return c.value
    for m in mentions:
        name = getattr(m, "name", None)
        if name:
            return str(name)
    if event.title:
        from ..tools.text_extract import find_company_name

        found = find_company_name(event.title)
        if found:
            return found
    return f"unknown-{event.event_id[:8]}"


def _dedupe_claims(claims: Sequence[Claim]) -> list[Claim]:
    """Collapse duplicate assertions, keeping the highest-confidence evidence.

    Claims with the same predicate but *different* values are retained so the
    verifier can surface contradictions rather than silently pick one.
    """
    best: dict[tuple[str, str], Claim] = {}
    for c in claims:
        key = (c.predicate, str(c.value))
        current = best.get(key)
        if current is None or c.confidence > current.confidence:
            best[key] = c
    return list(best.values())


async def compose_newsletter(
    editor: NewsletterEditor, ctx: PipelineContext, payload: NewsletterInput
) -> NewsletterDraft:
    return await editor.handle(ctx, payload)
