"""Human Review Queue: routes low-confidence/consequential items to an analyst."""

from __future__ import annotations

from ..models.agent_io import ReviewPacket, VerificationVerdict
from ..models.enums import Verdict


class HumanReviewQueue:
    """Deterministic router. Builds a compact evidence packet; no model calls."""

    name = "human-review-queue"

    def build_packet(
        self,
        *,
        item_id: str,
        item_type: str,
        summary: str,
        verdict: VerificationVerdict,
        evidence: list[str] | None = None,
    ) -> ReviewPacket:
        return ReviewPacket(
            item_id=item_id,
            item_type=item_type,
            summary=summary,
            confidence=verdict.confidence,
            reasons=list(verdict.reasons),
            evidence=evidence or [],
            status="pending",
        )

    def should_review(self, verdict: VerificationVerdict) -> bool:
        if verdict.verdict is Verdict.QUARANTINE:
            return True
        # Any contradiction or temporal failure must be seen by an analyst,
        # even if the item was otherwise rejected.
        if any(
            not f.passed and f.check in {"contradiction", "temporal", "provenance"}
            for f in verdict.findings
        ):
            return True
        # Publish verdicts that rely on a single non-A source still get a look.
        return verdict.verdict is Verdict.PUBLISH and verdict.confidence < 0.85
