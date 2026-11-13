"""Explainable momentum score produced by the deterministic Scoring service."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScoreFeatures(BaseModel):
    """Inputs to the momentum score. All optional; the service normalizes and weights."""

    total_disclosed_funding_usd: float = 0.0
    latest_round_stage: str | None = None
    rounds_count: int = 0
    investor_quality: float = 0.5
    founder_pedigree: float = 0.5
    traction: float = 0.5
    recency_days: float | None = None
    novelty: float = 0.5
    source_tier_score: float = 0.7
    corroboration_count: int = 1


class FactorContribution(BaseModel):
    """One weighted factor in the momentum score, always tied to evidence."""

    name: str
    raw_value: float
    normalized: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0)
    contribution: float
    evidence: list[str] = Field(default_factory=list)


class Score(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    percentile: float = Field(default=0.0, ge=0.0, le=1.0)
    factors: list[FactorContribution] = Field(default_factory=list)
    model_version: str = "momentum-v1"

    def explain(self) -> str:
        lines = [f"momentum={self.value:.3f} p{self.percentile * 100:.0f}"]
        for f in sorted(self.factors, key=lambda x: x.contribution, reverse=True):
            lines.append(
                f"  {f.name}: {f.raw_value:.3g} -> {f.contribution:.3f} (w={f.weight:.2f})"
            )
        return "\n".join(lines)
