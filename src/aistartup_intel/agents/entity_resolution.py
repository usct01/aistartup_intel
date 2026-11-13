"""Entity Resolver agent: dedupe companies/aliases via blocking + scoring.

Deterministic matching runs first; ambiguous cases are routed to human review.
"""

from __future__ import annotations

import re

from ..models.agent_io import (
    EntityResolutionDecision,
    EntityResolutionInput,
    EntityResolutionResult,
)
from .base import Agent, PipelineContext

_SUFFIXES = {
    "inc", "inc.", "llc", "ltd", "ltd.", "corp", "corp.", "co", "co.",
    "gmbh", "sa", "ag", "ai", "labs", "lab", "technologies", "technology", "the",
}
_MERGE_THRESHOLD = 0.9
_REVIEW_THRESHOLD = 0.6


def normalize_name(name: str) -> str:
    tokens = re.split(r"[^a-z0-9]+", name.lower())
    return " ".join(t for t in tokens if t and t not in _SUFFIXES)


def similarity(a: str, b: str) -> float:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    sa, sb = set(na.split()), set(nb.split())
    jaccard = len(sa & sb) / len(sa | sb)
    acronym = 1.0 if "".join(w[0] for w in na.split()) == nb.replace(" ", "") else 0.0
    prefix = 1.0 if na.startswith(nb) or nb.startswith(na) else 0.0
    return max(jaccard, acronym * 0.95, prefix * 0.8)


class EntityResolver(Agent[EntityResolutionInput, EntityResolutionResult]):
    name = "entity-resolver"
    model_role = "classifier_hard"
    description = "Resolves duplicates, aliases, rebrands, and investor names."

    async def handle(self, ctx: PipelineContext, payload: EntityResolutionInput) -> EntityResolutionResult:
        decisions: list[EntityResolutionDecision] = []
        needs_review: list[EntityResolutionDecision] = []
        for incoming in payload.incoming:
            best: EntityResolutionDecision | None = None
            for existing in payload.existing:
                score = similarity(incoming.name, existing.name)
                if best is None or score > best.score:
                    best = EntityResolutionDecision(
                        left_id=incoming.id,
                        left_name=incoming.name,
                        right_id=existing.id,
                        right_name=existing.name,
                        score=score,
                        decision="keep_separate",
                        reasons=[],
                    )
            if best is None:
                continue
            if best.score >= _MERGE_THRESHOLD:
                best.decision = "merge"
                best.reasons = [f"similarity {best.score:.2f} >= {_MERGE_THRESHOLD}"]
                decisions.append(best)
            elif best.score >= _REVIEW_THRESHOLD:
                best.decision = "review"
                best.reasons = [f"similarity {best.score:.2f} in review band"]
                decisions.append(best)
                needs_review.append(best)
            else:
                best.decision = "keep_separate"
                best.reasons = [f"similarity {best.score:.2f} below threshold"]
                decisions.append(best)
        return EntityResolutionResult(decisions=decisions, needs_review=needs_review)
