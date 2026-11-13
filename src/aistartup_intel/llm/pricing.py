"""Approximate USD-per-1M-token pricing for cost tracking.

Values are best-effort defaults for budgeting, not billing. Update as needed.
"""

from __future__ import annotations

# (prompt_usd_per_1m, completion_usd_per_1m)
PRICES: dict[str, tuple[float, float]] = {
    "openai/gpt-4o": (2.50, 10.00),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "anthropic/claude-3.5-sonnet": (3.00, 15.00),
    "google/gemini-2.0-flash-001": (0.10, 0.40),
    "deepseek/deepseek-chat": (0.14, 0.28),
}

DEFAULT_PRICE = (1.00, 3.00)


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p, c = PRICES.get(model, DEFAULT_PRICE)
    return (prompt_tokens / 1_000_000) * p + (completion_tokens / 1_000_000) * c
