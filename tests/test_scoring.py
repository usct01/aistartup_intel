from __future__ import annotations

from aistartup_intel.models.scoring import ScoreFeatures
from aistartup_intel.scoring.service import MomentumScorer


def test_scoring_is_reproducible():
    scorer = MomentumScorer()
    features = ScoreFeatures(total_disclosed_funding_usd=25_000_000, latest_round_stage="series_a")
    a = scorer.score(features)
    b = scorer.score(features)
    assert a.value == b.value
    assert [f.contribution for f in a.factors] == [f.contribution for f in b.factors]


def test_more_funding_scores_higher():
    scorer = MomentumScorer()
    low = scorer.score(ScoreFeatures(total_disclosed_funding_usd=3_000_000)).value
    high = scorer.score(ScoreFeatures(total_disclosed_funding_usd=300_000_000)).value
    assert high > low


def test_score_in_range_and_explainable():
    scorer = MomentumScorer()
    score = scorer.score(ScoreFeatures(total_disclosed_funding_usd=25_000_000))
    assert 0.0 <= score.value <= 1.0
    assert {f.name for f in score.factors} >= {"funding", "stage", "recency", "corroboration"}
    assert "momentum=" in score.explain()


def test_percentile_against_reference():
    scorer = MomentumScorer()
    score = scorer.score(
        ScoreFeatures(total_disclosed_funding_usd=25_000_000),
        reference_values=[0.1, 0.2, 0.3, 0.9],
    )
    assert 0.0 <= score.percentile <= 1.0
