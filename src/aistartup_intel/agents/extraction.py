"""Document Extractor agent.

Pulls company facts, funding amounts, investors, and dates from a document. Every
claim carries a verbatim evidence span; any claim whose span is not literally
present in the source is dropped (anti-hallucination).
"""

from __future__ import annotations

from ..models.agent_io import ExtractionResult, ExtractRequest
from ..models.enums import EntityType
from ..models.events import Claim, EntityMention, EvidenceSpan
from ..tools import text_extract as tx
from .base import Agent, PipelineContext


class DocumentExtractor(Agent[ExtractRequest, ExtractionResult]):
    name = "document-extractor"
    model_role = "extractor"
    description = "Extracts evidence-backed facts from a source document."

    async def handle(self, ctx: PipelineContext, payload: ExtractRequest) -> ExtractionResult:
        text = payload.text
        extracted_by = self.model if self.llm.online else "deterministic"
        claims: list[Claim] = []
        mentions: list[EntityMention] = []

        def claim(
            predicate: str, value: str | int | float | bool | None, confidence: float, span: str
        ) -> Claim:
            return Claim(
                predicate=predicate,
                value=value,
                confidence=confidence,
                evidence=EvidenceSpan(text=span, document_uri=payload.document_uri),
                extracted_by=extracted_by,
            )

        company = tx.find_company_name(text)
        if company:
            span = tx.verbatim_span(text, company)
            claims.append(claim("company_name", company, 0.7, span))
            mentions.append(
                EntityMention(name=company, type=EntityType.COMPANY, role="subject", confidence=0.7)
            )

        money = tx.find_money(text)
        if money:
            best = max(money, key=lambda m: m.amount_usd)
            claims.append(claim("raised_amount_usd", best.amount_usd, 0.6, best.span))

        round_info = tx.find_round_type(text)
        if round_info:
            rtype, span = round_info
            claims.append(claim("round_type", rtype, 0.6, span))

        for name, span in tx.find_investors(text):
            claims.append(claim("investor_mention", name, 0.55, span))
            mentions.append(
                EntityMention(
                    name=name, type=EntityType.INVESTOR, role="participant", confidence=0.55
                )
            )

        dates = tx.find_dates(text)
        if dates:
            d, span = dates[0]
            claims.append(claim("announced_on", d.isoformat(), 0.5, span))

        # Enforce the verbatim-evidence rule.
        claims = [c for c in claims if tx.present_verbatim(text, c.evidence.text)]

        return ExtractionResult(
            company_mentions=mentions,
            claims=claims,
            product_claims=[],
            model_used=extracted_by,
        )
