"""Matcher: keyword pre-filter + tolerant JSON parsing of the LLM response."""

import json

import pytest

from app.services.jobs import matcher
from app.services.jobs.models import JobPosting


def _job(**kw) -> JobPosting:
    base = dict(id="x:y:1", provider="lever", company="Y", title="Backend Engineer", description_text="")
    base.update(kw)
    return JobPosting(**base)


def test_keyword_overlap_high_for_related_role():
    resume = "Python FastAPI PostgreSQL Kubernetes distributed systems payments"
    job = _job(title="Backend Engineer", description_text="We use Python, FastAPI and Kubernetes for payments.")
    assert matcher.keyword_overlap(resume, job) > 0.3


def test_keyword_overlap_low_for_unrelated_role():
    resume = "Python FastAPI PostgreSQL Kubernetes distributed systems payments"
    job = _job(title="Recruiter", description_text="Own full-cycle recruiting and candidate relationships.")
    assert matcher.keyword_overlap(resume, job) < 0.1


def test_empty_resume_scores_everything():
    assert matcher.keyword_overlap("", _job()) == 1.0


class _FakeChoice:
    def __init__(self, content):
        self.message = type("M", (), {"content": content})


class _FakeCompletions:
    def __init__(self, content):
        self._content = content

    async def create(self, **_kw):
        return type("R", (), {"choices": [_FakeChoice(self._content)]})


class _FakeClient:
    def __init__(self, content):
        self.chat = type("C", (), {"completions": _FakeCompletions(content)})


@pytest.fixture(autouse=True)
def _fake_key(monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_score_job_parses_and_clamps(monkeypatch):
    payload = json.dumps(
        {"score": 250, "verdict": "nonsense", "summary": "ok", "matched_requirements": ["a"], "missing_requirements": ["b", "c"]}
    )
    monkeypatch.setattr(matcher, "AsyncOpenAI", lambda **_: _FakeClient(payload))
    result = await matcher.score_job("resume", _job())
    assert result.score == 100
    assert result.verdict == "strong"  # derived from the clamped score
    assert result.matched_requirements == ["a"]


async def test_score_job_soft_fails_on_bad_json(monkeypatch):
    monkeypatch.setattr(matcher, "AsyncOpenAI", lambda **_: _FakeClient("not json"))
    result = await matcher.score_job("resume", _job())
    assert result.verdict == "error"
    assert result.error
