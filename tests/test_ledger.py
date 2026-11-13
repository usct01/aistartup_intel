from __future__ import annotations

from aistartup_intel.store import repository as repo


def test_ledger_is_append_only_and_ordered(session):
    repo.append_ledger(session, record_type="company", record_id="c1", action="created",
                       payload={"name": "Acme"})
    repo.append_ledger(session, record_type="company", record_id="c1", action="updated",
                       payload={"name": "Acme AI"})
    entries = repo.ledger_for(session, "c1")
    assert [e.action for e in entries] == ["created", "updated"]
    # Nothing is overwritten: both entries remain.
    assert len(entries) == 2


def test_run_manifest_lifecycle(session):
    run = repo.start_run(session, input_ref="evt-1")
    assert run.status == "running"
    repo.finish_run(session, run.run_id, agents=[{"agent": "verifier"}], total_tokens=100,
                    cost_usd=0.01, decisions={"verdict": "publish"})
    loaded = repo.get_run(session, run.run_id)
    assert loaded is not None
    assert loaded.status == "completed"
    assert loaded.decisions["verdict"] == "publish"


def test_review_queue_roundtrip(session):
    row = repo.enqueue_review(session, item_id="c1", item_type="company", summary="s",
                              confidence=0.4, reasons=["low confidence"])
    assert repo.list_reviews(session, status="pending")[0].id == row.id
    repo.resolve_review(session, row.id, status="approved", resolver="analyst")
    assert len(repo.list_reviews(session, status="pending")) == 0
    assert len(repo.list_reviews(session, status="approved")) == 1
