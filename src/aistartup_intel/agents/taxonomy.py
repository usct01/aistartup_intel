"""Taxonomy Classifier agent: multi-axis labeling (vertical/capability/buyer/maturity)."""

from __future__ import annotations

from ..models.agent_io import ClassifyInput, TaxonomyResult
from ..models.domain import TaxonomyTag
from .base import Agent, PipelineContext

_VERTICALS = {
    "healthcare": [
        "health", "clinical", "patient", "medical", "diagnos", "drug discovery", "genomic", "care",
    ],
    "legal": [
        "legal", "contract", "litigation", "e-discovery", "ediscovery", "law firm", "compliance", "ip ",
    ],
    "finance": [
        "fintech", "banking", "trading", "underwriting", "lending", "insurance", "payments",
        "aml", "kyc", "treasury",
    ],
}

_CAPABILITIES = {
    "foundation-models": ["foundation model", "llm", "large language", "multimodal", "transformer"],
    "agents": ["agent", "agentic", "tool-use", "workflow automation", "copilot"],
    "infrastructure": ["inference", "serving", "gpu", "vector database", "rag", "orchestration", "hosting"],
    "data": ["data label", "synthetic data", "data pipeline", "knowledge graph", "dataset"],
    "trust-governance": ["governance", "model risk", "explainab", "audit", "responsible ai"],
    "security": ["security", "prompt injection", "red team", "deepfake", "provenance", "watermark"],
    "robotics": ["robot", "autonomous", "computer vision", "digital twin", "embodied"],
}

_BUYERS = {
    "enterprise": ["enterprise", "b2b", "fortune 500", "compliance team"],
    "consumer": ["consumer", "prosumer", "personal", "b2c"],
    "developer": ["developer", "sdk", "api", "devops"],
    "smb": ["smb", "small business", "startup"],
    "government": ["government", "public sector", "defense"],
}


class TaxonomyClassifier(Agent[ClassifyInput, TaxonomyResult]):
    name = "taxonomy-classifier"
    model_role = "classifier_bulk"
    description = "Assigns vertical, AI layer, buyer, and maturity labels."

    async def handle(self, ctx: PipelineContext, payload: ClassifyInput) -> TaxonomyResult:
        text = f"{payload.company_name} {payload.text}".lower()
        tags: list[TaxonomyTag] = []

        for axis, table in (("vertical", _VERTICALS), ("capability", _CAPABILITIES), ("buyer", _BUYERS)):
            for label, keywords in table.items():
                hits = sum(1 for kw in keywords if kw in text)
                if hits:
                    confidence = min(0.9, 0.5 + 0.15 * hits)
                    tags.append(TaxonomyTag(axis=axis, label=label, confidence=confidence))

        maturity = _maturity_label(payload.total_funding_usd)
        tags.append(TaxonomyTag(axis="maturity", label=maturity, confidence=0.6))

        uncertain = not any(t.axis == "vertical" for t in tags)
        return TaxonomyResult(tags=tags, uncertain=uncertain, model_used="deterministic")


def _maturity_label(total: float | None) -> str:
    if total is None:
        return "unknown"
    if total < 10_000_000:
        return "early"
    if total < 100_000_000:
        return "growth"
    return "mature"
