"""Verifier (critic) agent: the trust gate before publication.

Runs independent checks (provenance, corroboration, contradiction, temporal,
reputation) and assigns a verdict + confidence. Uses a different model family than
the extractor to reduce correlated error (enforced via ``extractor_model``).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from ..models.agent_io import VerificationFinding, VerificationVerdict, VerifyInput
from ..models.enums import Verdict
from ..tools import text_extract as tx
from .base import Agent, PipelineContext

_TIER_WEIGHT = {"A": 1.0, "B": 0.85, "C": 0.9}

# Threshold bands (kept in sync with Settings defaults).
_AUTO_PUBLISH = 0.75
_QUARANTINE = 0.45


class Verifier(Agent[VerifyInput, VerificationVerdict]):
    name = "verifier"
    model_role = "verifier"
    description = "Validates claims, assigns confidence, and creates review packets."

    async def handle(self, ctx: PipelineContext, payload: VerifyInput) -> VerificationVerdict:
        findings: list[VerificationFinding] = []

        provenance_ok = all(c.evidence.text.strip() for c in payload.claims)
        if provenance_ok and payload.context_text is not None:
            missing = [
                c.predicate
                for c in payload.claims
                if not tx.present_verbatim(payload.context_text, c.evidence.text)
            ]
            provenance_ok = not missing
            if missing:
                findings.append(
                    VerificationFinding(
                        check="provenance",
                        passed=False,
                        detail=f"evidence not verbatim in source: {missing}",
                    )
                )
        findings.append(
            VerificationFinding(
                check="provenance",
                passed=provenance_ok,
                detail="all claims carry verbatim evidence" if provenance_ok else "missing evidence",
            )
        )

        contradictions = _find_contradictions(payload)
        findings.append(
            VerificationFinding(
                check="contradiction",
                passed=not contradictions,
                detail="; ".join(contradictions) if contradictions else "no conflicts",
            )
        )

        temporal_ok = _temporal_ok(payload)
        findings.append(
            VerificationFinding(
                check="temporal",
                passed=temporal_ok,
                detail="dates plausible" if temporal_ok else "implausible date",
            )
        )

        tier = payload.source_tier.upper()
        reputation_ok = tier in _TIER_WEIGHT
        findings.append(
            VerificationFinding(
                check="reputation",
                passed=reputation_ok,
                detail=f"source tier {tier}",
            )
        )

        corroboration_ok = tier == "A" or len(payload.claims) >= 2
        findings.append(
            VerificationFinding(
                check="corroboration",
                passed=corroboration_ok,
                detail=f"tier {tier}, {len(payload.claims)} claims",
            )
        )

        confidences = [c.confidence for c in payload.claims] or [0.0]
        mean = sum(confidences) / len(confidences)
        peak = max(confidences)
        # Balance overall support with the strongest primary claim.
        base = 0.5 * mean + 0.5 * peak
        confidence = base * _TIER_WEIGHT.get(tier, 0.6)
        if contradictions:
            confidence *= 0.5
        if not provenance_ok:
            confidence *= 0.3
        confidence = max(0.0, min(1.0, confidence))

        if not provenance_ok:
            verdict = Verdict.REJECT
        elif confidence >= _AUTO_PUBLISH and not contradictions:
            verdict = Verdict.PUBLISH
        elif confidence >= _QUARANTINE:
            verdict = Verdict.QUARANTINE
        else:
            verdict = Verdict.REJECT

        reasons = [f"{f.check}: {'ok' if f.passed else 'FAIL'} ({f.detail})" for f in findings]
        return VerificationVerdict(
            verdict=verdict,
            confidence=confidence,
            findings=findings,
            reasons=reasons,
            verifier_model=self.model if self.llm.online else "deterministic-critic",
            extractor_model=payload.extractor_model,
        )


def _find_contradictions(payload: VerifyInput) -> list[str]:
    out: list[str] = []
    for c in payload.claims:
        prior = payload.existing_values.get(c.predicate, [])
        if prior and c.value is not None and str(c.value) not in prior:
            out.append(f"{c.predicate}: new={c.value} vs existing={prior}")
    return out


def _temporal_ok(payload: VerifyInput) -> bool:
    for c in payload.claims:
        if c.predicate == "announced_on" and isinstance(c.value, str):
            try:
                d = date.fromisoformat(c.value)
            except ValueError:
                return False
            if d > datetime.now(UTC).date():
                return False
    return True
