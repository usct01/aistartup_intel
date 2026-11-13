"""Deterministic, evidence-spanning extractors.

These functions never invent text: every returned span is a literal substring of
the input, satisfying the evidence standard. They back the Document Extractor and
Funding Analyst when running offline, and provide a fallback when models fail.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

_MULT = {
    "million": 1e6, "mil": 1e6, "m": 1e6,
    "billion": 1e9, "bil": 1e9, "b": 1e9,
    "thousand": 1e3, "k": 1e3,
    "": 1.0, None: 1.0,
}

_MONEY = re.compile(
    r"(?:\$\s?|usd\s?)\s?([\d][\d,\.]*)\s?(million|billion|thousand|mil|bil|[mbk])?\b",
    re.IGNORECASE,
)

_ROUNDS = [
    ("pre-seed", "pre_seed"), ("preseed", "pre_seed"), ("pre seed", "pre_seed"),
    ("seed", "seed"),
    ("series a", "series_a"), ("series b", "series_b"), ("series c", "series_c"),
    ("series d", "series_d"), ("series e", "series_e"),
    ("growth", "growth"), ("debt", "debt"), ("grant", "grant"),
]

_INVESTOR_LEAD = re.compile(
    r"(?:led by|led round by|backed by|investors? include|participated?|from)\s+"
    r"([A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*){0,4})",
)

_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


@dataclass(frozen=True)
class MoneyHit:
    amount_usd: float
    span: str


def find_money(text: str) -> list[MoneyHit]:
    hits: list[MoneyHit] = []
    for match in _MONEY.finditer(text):
        raw = match.group(1).replace(",", "")
        try:
            value = float(raw)
        except ValueError:
            continue
        mult = _MULT.get((match.group(2) or "").lower())
        if mult is None:
            mult = 1.0
        hits.append(MoneyHit(amount_usd=value * mult, span=match.group(0).strip()))
    return hits


def find_round_type(text: str) -> tuple[str, str] | None:
    lowered = text.lower()
    for needle, rtype in _ROUNDS:
        idx = lowered.find(needle)
        if idx != -1:
            return rtype, text[idx : idx + len(needle)]
    return None


def find_investors(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for match in _INVESTOR_LEAD.finditer(text):
        name = match.group(1).strip().rstrip(".,")
        if 2 <= len(name) <= 80:
            found.append((name, match.group(0).strip()))
    return found


def find_dates(text: str) -> list[tuple[date, str]]:
    out: list[tuple[date, str]] = []
    for match in _DATE.finditer(text):
        try:
            out.append((date.fromisoformat(match.group(1)), match.group(0)))
        except ValueError:
            continue
    return out


def find_company_name(text: str) -> str | None:
    """Heuristic: the subject before a funding verb, else the first Proper Noun run."""
    for verb in ("raised", "raises", "secures", "closed", "announced", "filed"):
        idx = text.lower().find(verb)
        if idx > 0:
            head = text[:idx].strip().rstrip(",. ")
            if 1 < len(head) <= 80:
                return head
    match = re.search(r"\b([A-Z][A-Za-z0-9&.\-]*(?:\s+[A-Z][A-Za-z0-9&.\-]*){0,3})\b", text)
    return match.group(1) if match else None


def verbatim_span(text: str, needle: str, pad: int = 20) -> str:
    """Return a literal substring of ``text`` containing ``needle`` (or a short head)."""
    if not needle:
        return text[: min(len(text), 80)]
    idx = text.find(needle)
    if idx == -1:
        idx = text.lower().find(needle.lower())
    if idx == -1:
        return text[: min(len(text), 80)]
    return text[max(0, idx - pad) : min(len(text), idx + len(needle) + pad)].strip()


def present_verbatim(text: str, span: str) -> bool:
    return bool(span) and span in text
