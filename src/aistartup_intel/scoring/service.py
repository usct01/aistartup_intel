"""Deterministic momentum scoring service.

Transparent weighted model (MVP). Every factor is normalized to [0, 1], weighted,
and reported in the breakdown so a score can always be explained from evidence.
Identical inputs always produce identical scores (reproducible).
"""

from __future__ import annotations

import math

from ..models.scoring import FactorContribution, Score, ScoreFeatures

# Configurable weights (experiment-friendly; sum need not be 1).
DEFAULT_WEIGHTS: dict[str, float] = {
    "funding": 0.30,
    "stage": 0.15,
    "investor_quality": 0.10,
    "founder_pedigree": 0.10,
    "traction": 0.15,
    "recency": 0.10,
    "novelty": 0.05,
    "corroboration": 0.05,
}

_STAGE_ORDER = ["pre_seed", "seed", "series_a", "series_b", "series_c", "series_d", "series_e", "growth"]


def _norm_funding(total_usd: float) -> float:
    # Log scale: $10M -> ~0.5, $100M -> ~0.75, $1B -> ~1.0
    if total_usd <= 0:
        return 0.0
    return max(0.0, min(1.0, math.log10(total_usd / 1_000_000 + 1) / 3.0))


def _norm_stage(stage: str | None) -> float:
    if stage in _STAGE_ORDER:
        return (_STAGE_ORDER.index(stage) + 1) / len(_STAGE_ORDER)
    return 0.25


def _norm_recency(days: float | None) -> float:
    if days is None:
        return 0.5
    return max(0.0, min(1.0, math.exp(-days / 180.0)))


def _norm_corroboration(count: int) -> float:
    return min(1.0, count / 3.0)


class MomentumScorer:
    model_version = "momentum-v1"

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = dict(weights or DEFAULT_WEIGHTS)

    def score(
        self,
        features: ScoreFeatures,
        *,
        evidence: dict[str, list[str]] | None = None,
        reference_values: list[float] | None = None,
    ) -> Score:
        evidence = evidence or {}
        raw: dict[str, tuple[float, float, str]] = {
            "funding": (
                features.total_disclosed_funding_usd,
                _norm_funding(features.total_disclosed_funding_usd),
                f"${features.total_disclosed_funding_usd:,.0f}",
            ),
            "stage": (
                float(_STAGE_ORDER.index(features.latest_round_stage) + 1)
                if features.latest_round_stage in _STAGE_ORDER
                else 0.0,
                _norm_stage(features.latest_round_stage),
                features.latest_round_stage or "unknown",
            ),
            "investor_quality": (features.investor_quality, features.investor_quality, ""),
            "founder_pedigree": (features.founder_pedigree, features.founder_pedigree, ""),
            "traction": (features.traction, features.traction, ""),
            "recency": (
                features.recency_days if features.recency_days is not None else -1,
                _norm_recency(features.recency_days),
                f"{features.recency_days:.0f}d" if features.recency_days is not None else "unknown",
            ),
            "novelty": (features.novelty, features.novelty, ""),
            "corroboration": (
                float(features.corroboration_count),
                _norm_corroboration(features.corroboration_count),
                f"{features.corroboration_count} sources",
            ),
        }
        # Reputation factor multiplies the whole score modestly.
        source_factor = max(0.0, min(1.0, features.source_tier_score))

        factors: list[FactorContribution] = []
        weighted_sum = 0.0
        weight_total = 0.0
        for name, (raw_value, normalized, label) in raw.items():
            weight = self.weights.get(name, 0.0)
            contribution = normalized * weight
            weighted_sum += contribution
            weight_total += weight
            ev = list(evidence.get(name, []))
            if label:
                ev = [label, *ev]
            factors.append(
                FactorContribution(
                    name=name,
                    raw_value=float(raw_value),
                    normalized=normalized,
                    weight=weight,
                    contribution=contribution,
                    evidence=ev,
                )
            )
        base = weighted_sum / weight_total if weight_total else 0.0
        value = max(0.0, min(1.0, base * (0.7 + 0.3 * source_factor)))
        percentile = _percentile(value, reference_values)
        return Score(
            value=value,
            percentile=percentile,
            factors=factors,
            model_version=self.model_version,
        )


def _percentile(value: float, reference: list[float] | None) -> float:
    if not reference:
        return value
    below = sum(1 for v in reference if v <= value)
    return below / len(reference)
