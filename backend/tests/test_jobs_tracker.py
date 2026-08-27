"""Applied-jobs tracker persistence + upsert-by-job semantics."""

from types import SimpleNamespace

import pytest

from app.services.jobs import tracker


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "APPLICATIONS_PATH", tmp_path / "applications.json")
    yield


def _job(**kw):
    base = dict(id="greenhouse:acme:1", company="Acme", title="Engineer", url="https://x", provider="greenhouse")
    base.update(kw)
    return SimpleNamespace(**base)


def test_add_list_update_delete():
    a = tracker.add_application(tracker.ApplicationCreate(company="Foo", title="Dev", status="applied"))
    assert [x.id for x in tracker.list_applications()] == [a.id]

    updated = tracker.update_application(a.id, tracker.ApplicationUpdate(status="interviewing", notes="call mon"))
    assert updated.status == "interviewing" and updated.notes == "call mon"

    assert tracker.delete_application(a.id) is True
    assert tracker.list_applications() == []


def test_record_apply_upserts_by_job_and_does_not_downgrade():
    tracker.record_apply(_job(), status="preparing", source="apply")
    row = tracker.list_applications()[0]
    assert row.status == "preparing" and row.company == "Acme"

    # user advances it
    tracker.update_application(row.id, tracker.ApplicationUpdate(status="interviewing"))

    # a later prepare for the same job must not knock it back to 'preparing'
    tracker.record_apply(_job(), status="preparing", source="apply")
    assert tracker.list_applications()[0].status == "interviewing"

    # but a real submit does advance it
    tracker.record_apply(_job(), status="applied", source="submit")
    assert tracker.list_applications()[0].status == "applied"
    assert len(tracker.list_applications()) == 1
