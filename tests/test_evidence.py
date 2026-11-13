from __future__ import annotations

from aistartup_intel.tools import text_extract as tx


def test_money_spans_are_verbatim_substrings():
    text = "Acme AI raised $12.5M seed led by Sequoia to build agents."
    hits = tx.find_money(text)
    assert hits
    for hit in hits:
        assert hit.span in text


def test_money_scales_million_billion():
    assert tx.find_money("raised $2 million")[0].amount_usd == 2_000_000
    assert tx.find_money("raised $1.5B")[0].amount_usd == 1_500_000_000


def test_round_type_and_investors():
    text = "LedgerMind raised $40M Series B led by Ribbit Capital."
    rtype = tx.find_round_type(text)
    assert rtype is not None and rtype[0] == "series_b"
    investors = tx.find_investors(text)
    assert any(name.startswith("Ribbit") for name, _ in investors)
    for _, span in investors:
        assert span in text


def test_verbatim_span_and_presence():
    text = "Acme AI raised $5M."
    span = tx.verbatim_span(text, "$5M")
    assert tx.present_verbatim(text, span)
    assert span in text


def test_company_name_before_funding_verb():
    assert tx.find_company_name("Acme AI raised $5M seed") == "Acme AI"
