"""Company registry search."""

from app.services.jobs.ats.registry import _entries, search_registry


def test_registry_loads():
    entries = _entries()
    assert len(entries) > 20
    assert all(e.provider in {"greenhouse", "lever", "ashby"} for e in entries)


def test_search_prefix_wins_over_substring():
    results = search_registry("st")
    names = [e.name for e in results]
    assert "Stripe" in names
    # A prefix match ("Stripe") should rank before a mid-word match.
    assert names.index("Stripe") == 0 or names[0].lower().startswith("st")


def test_search_case_insensitive_and_limited():
    assert any(e.slug == "openai" for e in search_registry("OPENAI"))
    assert len(search_registry("", limit=5)) == 5


def test_search_no_match():
    assert search_registry("zzznotacompany") == []
