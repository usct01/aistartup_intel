"""Typed inputs/outputs for every agent. Handoffs are structured data only."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from .domain import FundingRound, TaxonomyTag
from .enums import RoundType, Verdict
from .events import Claim, EntityMention


class CoverageRequest(BaseModel):
    """Input to the Research Planner describing what coverage is needed."""

    verticals: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    max_tasks: int = 10


class ResearchTask(BaseModel):
    """A unit of work emitted by the Research Planner."""

    task_id: str
    vertical: str
    category: str | None = None
    query: str
    rationale: str
    priority: int = Field(default=3, ge=1, le=5)


class ResearchPlan(BaseModel):
    tasks: list[ResearchTask] = Field(default_factory=list)
    coverage_notes: str | None = None


class SourceCandidate(BaseModel):
    """A source discovered by the Source Discovery agent."""

    url: str
    source_type: str  # company_site, pressroom, investor_portfolio, rss, registry, filing, news
    tier: str = "B"
    title: str | None = None
    rationale: str | None = None


class DiscoveryResult(BaseModel):
    candidates: list[SourceCandidate] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class CrawlDocument(BaseModel):
    uri: str
    url: str
    content_type: str
    text: str
    fetched_at: datetime
    from_cache: bool = False
    http_status: int | None = None


class CrawlResult(BaseModel):
    documents: list[CrawlDocument] = Field(default_factory=list)
    paused_sources: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class ExtractRequest(BaseModel):
    """A document (or event text) to extract facts from."""

    text: str
    source_id: str
    source_tier: str = "B"
    url: str | None = None
    document_uri: str | None = None


class ExtractionResult(BaseModel):
    """Structured facts pulled from a document, all evidence-backed."""

    company_mentions: list[EntityMention] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    product_claims: list[str] = Field(default_factory=list)
    model_used: str | None = None


class FundingAnalysisInput(BaseModel):
    claims: list[Claim] = Field(default_factory=list)
    company_ref: str | None = None
    context_text: str | None = None


class FundingAnalysis(BaseModel):
    rounds: list[FundingRound] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


class EntityRef(BaseModel):
    id: str | None = None
    name: str


class EntityResolutionInput(BaseModel):
    existing: list[EntityRef] = Field(default_factory=list)
    incoming: list[EntityRef] = Field(default_factory=list)


class EntityResolutionDecision(BaseModel):
    left_id: str | None
    left_name: str
    right_id: str | None
    right_name: str
    score: float = Field(ge=0.0, le=1.0)
    decision: str  # merge | keep_separate | review
    reasons: list[str] = Field(default_factory=list)


class EntityResolutionResult(BaseModel):
    decisions: list[EntityResolutionDecision] = Field(default_factory=list)
    needs_review: list[EntityResolutionDecision] = Field(default_factory=list)


class ClassifyInput(BaseModel):
    company_name: str
    text: str = ""
    total_funding_usd: float | None = None


class TaxonomyResult(BaseModel):
    tags: list[TaxonomyTag] = Field(default_factory=list)
    uncertain: bool = False
    model_used: str | None = None


class SignalInput(BaseModel):
    company_name: str
    event_kinds: list[str] = Field(default_factory=list)
    funding_rounds: list[FundingRound] = Field(default_factory=list)
    text: str = ""


class SignalResult(BaseModel):
    signals: list[dict[str, Any]] = Field(default_factory=list)


class VerifyInput(BaseModel):
    claims: list[Claim] = Field(default_factory=list)
    source_tier: str = "B"
    source_id: str = ""
    context_text: str | None = None
    existing_values: dict[str, list[str]] = Field(default_factory=dict)
    extractor_model: str | None = None


class VerificationFinding(BaseModel):
    check: str  # corroboration | provenance | contradiction | temporal | reputation
    passed: bool
    detail: str


class VerificationVerdict(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    findings: list[VerificationFinding] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    verifier_model: str | None = None
    extractor_model: str | None = None

    @property
    def independent_from_extractor(self) -> bool:
        """Anti-correlation: verifier family must differ from extractor family."""
        if not self.verifier_model or not self.extractor_model:
            return False
        return self.verifier_model.split("/")[0] != self.extractor_model.split("/")[0]


class ReviewPacket(BaseModel):
    item_id: str
    item_type: str
    summary: str
    confidence: float
    reasons: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    status: str = "pending"


class NewsletterItem(BaseModel):
    company: str
    headline: str
    body: str
    confidence: float
    evidence_urls: list[str] = Field(default_factory=list)
    score: float | None = None


class NewsletterInput(BaseModel):
    user_email: str
    verticals: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    min_funding_usd: int = 0
    items: list[NewsletterItem] = Field(default_factory=list)
    edition_date: date | None = None


class NewsletterDraft(BaseModel):
    subject: str
    vertical_pulse: dict[str, str] = Field(default_factory=dict)
    items: list[NewsletterItem] = Field(default_factory=list)
    generated_at: datetime | None = None


class EvalSample(BaseModel):
    claims_total: int
    claims_supported: int
    claims_correct: int


class EvalInput(BaseModel):
    samples: list[EvalSample] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    sample_size: int
    hallucination_rate: float
    precision: float
    coverage: float
    notes: list[str] = Field(default_factory=list)


class FundingRoundHint(BaseModel):
    round_type: RoundType = RoundType.OTHER
    amount_usd: float | None = None
    announced_on: date | None = None
    lead: str | None = None
