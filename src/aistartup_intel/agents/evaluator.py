"""Quality Evaluator agent: sampled hallucination/coverage/precision metrics."""

from __future__ import annotations

from ..models.agent_io import EvalInput, EvaluationResult
from .base import Agent, PipelineContext


class QualityEvaluator(Agent[EvalInput, EvaluationResult]):
    name = "quality-evaluator"
    model_role = "evaluator"
    description = "Runs sampled evaluations for hallucinations, coverage, and precision."

    async def handle(self, ctx: PipelineContext, payload: EvalInput) -> EvaluationResult:
        total = sum(s.claims_total for s in payload.samples)
        supported = sum(s.claims_supported for s in payload.samples)
        correct = sum(s.claims_correct for s in payload.samples)
        notes: list[str] = []
        if total == 0:
            notes.append("no claims in sample")
        hallucination_rate = (total - supported) / total if total else 0.0
        precision = correct / total if total else 0.0
        coverage = supported / total if total else 0.0
        if hallucination_rate > 0.02:
            notes.append("hallucination rate exceeds 2% target")
        return EvaluationResult(
            sample_size=len(payload.samples),
            hallucination_rate=hallucination_rate,
            precision=precision,
            coverage=coverage,
            notes=notes,
        )
