"""FastAPI surface: search, companies, funding, review queue, newsletter preview."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents.base import PipelineContext
from ..agents.newsletter import NewsletterEditor
from ..config.settings import get_settings
from ..llm.gateway import LLMGateway
from ..models.agent_io import NewsletterInput, NewsletterItem
from ..store import db
from ..store import repository as repo
from ..store.tables import CompanyRow, FundingRoundRow, TaxonomyTagRow

settings = get_settings()


def get_session() -> Iterator[Session]:
    with db.session_scope() as session:
        yield session


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    db.init_db()
    yield


app = FastAPI(
    title="AI Startup Signal",
    version="0.1.0",
    description="Investor-first AI startup intelligence: companies, funding, signals, newsletter.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.get("/taxonomy")
def get_taxonomy(
    session: Session = Depends(get_session), axis: str | None = None
) -> dict[str, Any]:
    """Topics and subtopics with company counts, grouped by axis."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for ax, label, count in repo.list_taxonomy(session, axis=axis):
        grouped.setdefault(ax, []).append({"label": label, "count": count})
    return {"axes": grouped}


@app.get("/companies")
def list_companies(
    session: Session = Depends(get_session),
    min_total_funding_usd: float | None = Query(default=None, description="Total disclosed funding gate"),
    vertical: str | None = None,
    capability: str | None = None,
    buyer: str | None = None,
    q: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> dict[str, Any]:
    rows = repo.list_companies(
        session,
        min_total_funding_usd=min_total_funding_usd,
        vertical=vertical,
        capability=capability,
        buyer=buyer,
        q=q,
        limit=limit,
        offset=offset,
    )
    return {
        "count": len(rows),
        "companies": [
            {
                "id": c.id,
                "name": c.canonical_name,
                "url": c.url,
                "hq": c.hq,
                "description": c.description,
                "total_disclosed_funding_usd": total,
                "confidence": c.confidence,
                "is_new": c.is_new,
            }
            for c, total in rows
        ],
    }


@app.get("/companies/{company_id}")
def get_company(company_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    company = repo.get_company(session, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    rounds = repo.list_funding_rounds(session, company_id=company_id)
    tags = session.scalars(
        select(TaxonomyTagRow).where(TaxonomyTagRow.company_id == company_id)
    ).all()
    return {
        "id": company.id,
        "name": company.canonical_name,
        "url": company.url,
        "description": company.description,
        "hq": company.hq,
        "total_disclosed_funding_usd": repo.company_total_disclosed_funding(session, company_id),
        "funding_rounds": [
            {
                "id": r.id,
                "round_type": r.round_type,
                "amount_usd": r.amount_usd,
                "announced_on": r.announced_on.isoformat() if r.announced_on else None,
                "confidence": r.confidence,
            }
            for r in rounds
        ],
        "taxonomy": [{"axis": t.axis, "label": t.label, "confidence": t.confidence} for t in tags],
        "ledger": [
            {"action": entry.action, "type": entry.record_type, "at": entry.written_at.isoformat()}
            for entry in repo.ledger_for(session, company_id)
        ],
    }


@app.get("/funding")
def list_funding(
    session: Session = Depends(get_session),
    min_amount_usd: float | None = None,
    company_id: str | None = None,
) -> dict[str, Any]:
    rounds = repo.list_funding_rounds(
        session, company_id=company_id, min_amount_usd=min_amount_usd
    )
    company_names = {
        c.id: c.canonical_name for c in session.scalars(select(CompanyRow)).all()
    }
    return {
        "count": len(rounds),
        "rounds": [
            {
                "id": r.id,
                "company": company_names.get(r.company_id, r.company_id),
                "round_type": r.round_type,
                "amount_usd": r.amount_usd,
                "announced_on": r.announced_on.isoformat() if r.announced_on else None,
                "confidence": r.confidence,
            }
            for r in rounds
        ],
    }


@app.get("/events")
def list_events(
    session: Session = Depends(get_session),
    kind: str | None = None,
    unprocessed_only: bool = False,
    limit: int = Query(default=50, le=200),
) -> dict[str, Any]:
    rows = repo.list_events(session, kind=kind, unprocessed_only=unprocessed_only, limit=limit)
    return {
        "count": len(rows),
        "events": [
            {
                "event_id": e.event_id,
                "source_id": e.source_id,
                "kind": e.kind,
                "title": e.title,
                "processed": e.processed,
                "observed_at": e.observed_at.isoformat(),
            }
            for e in rows
        ],
    }


@app.get("/review")
def list_review(session: Session = Depends(get_session), status: str = "pending") -> dict[str, Any]:
    rows = repo.list_reviews(session, status=status)
    return {
        "count": len(rows),
        "items": [
            {
                "id": r.id,
                "item_id": r.item_id,
                "item_type": r.item_type,
                "summary": r.summary,
                "confidence": r.confidence,
                "reasons": r.reasons,
                "evidence": r.evidence,
                "status": r.status,
            }
            for r in rows
        ],
    }


@app.post("/review/{review_id}/resolve")
def resolve_review(
    review_id: str,
    status: str = Query(pattern="^(approved|rejected)$"),
    resolver: str = "analyst",
    note: str | None = None,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    row = repo.resolve_review(session, review_id, status=status, resolver=resolver, note=note)
    if row is None:
        raise HTTPException(status_code=404, detail="review item not found")
    return {"id": row.id, "status": row.status, "resolver": row.resolver}


@app.get("/runs/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    row = repo.get_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "run_id": row.run_id,
        "status": row.status,
        "agents": row.agents,
        "cost_usd": row.cost_usd,
        "total_tokens": row.total_tokens,
        "decisions": row.decisions,
        "replayable": row.replayable,
    }


@app.post("/newsletter/preview")
async def newsletter_preview(
    verticals: list[str] = Query(default_factory=list),
    min_funding_usd: float = 0.0,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    items: list[NewsletterItem] = []
    for company, total in repo.list_companies(
        session, min_total_funding_usd=min_funding_usd if min_funding_usd else None, limit=20
    ):
        latest = session.scalar(
            select(FundingRoundRow.amount_usd)
            .where(FundingRoundRow.company_id == company.id)
            .order_by(FundingRoundRow.announced_on.desc().nullslast())
            .limit(1)
        )
        items.append(
            NewsletterItem(
                company=company.canonical_name,
                headline=f"{company.canonical_name} funding update",
                body=f"Total disclosed funding ${total:,.0f}."
                + (f" Latest round ${latest:,.0f}." if latest else ""),
                confidence=company.confidence,
                evidence_urls=[company.url] if company.url else [],
                score=min(1.0, total / 100_000_000),
            )
        )
    ctx = PipelineContext(
        settings=settings, llm=LLMGateway(settings=settings), run_id="api", session=session
    )
    draft = await NewsletterEditor(ctx.llm).handle(
        ctx,
        NewsletterInput(
            user_email="api@example.com",
            verticals=verticals,
            min_funding_usd=int(min_funding_usd),
            items=items,
            edition_date=datetime.now(UTC).date(),
        ),
    )
    return draft.model_dump(mode="json")


class SubscribeRequest(BaseModel):
    email: str = Field(min_length=3)
    name: str | None = None
    verticals: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    min_funding_usd: int = Field(default=0, ge=0)


@app.post("/newsletter/subscribe", status_code=201)
def subscribe(payload: SubscribeRequest, session: Session = Depends(get_session)) -> dict[str, Any]:
    """Create or update a subscriber and their newsletter preferences (idempotent)."""
    if "@" not in payload.email or "." not in payload.email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="invalid email address")
    user, created = repo.create_user(session, email=payload.email, name=payload.name)
    existing = repo.get_subscription(session, user.id)
    if existing is None:
        subscription = repo.add_subscription(
            session,
            user_id=user.id,
            verticals=payload.verticals,
            categories=payload.capabilities,
            min_funding_usd=payload.min_funding_usd,
        )
    else:
        existing.verticals = list(payload.verticals)
        existing.categories = list(payload.capabilities)
        existing.min_funding_usd = payload.min_funding_usd
        existing.active = True
        session.flush()
        subscription = existing
    return {
        "user_id": user.id,
        "email": user.email,
        "created": created,
        "subscription": {
            "verticals": subscription.verticals,
            "capabilities": subscription.categories,
            "min_funding_usd": subscription.min_funding_usd,
            "active": subscription.active,
        },
    }


@app.get("/newsletter/subscription")
def get_subscription(
    email: str = Query(...), session: Session = Depends(get_session)
) -> dict[str, Any]:
    user = repo.get_user_by_email(session, email)
    if user is None:
        raise HTTPException(status_code=404, detail="subscriber not found")
    subscription = repo.get_subscription(session, user.id)
    return {
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "subscribed": subscription is not None and subscription.active,
        "verticals": subscription.verticals if subscription else [],
        "capabilities": subscription.categories if subscription else [],
        "min_funding_usd": subscription.min_funding_usd if subscription else 0,
    }


@app.get("/stats")
def stats(session: Session = Depends(get_session)) -> dict[str, Any]:
    return {
        "companies": repo.count_companies(session),
        "pending_reviews": len(repo.list_reviews(session, status="pending")),
        "subscribers": len(repo.list_subscribers(session)),
    }
