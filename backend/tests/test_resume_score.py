"""Resume ⇄ JD match report: deterministic keyword coverage, fallback, and
tolerant parsing of the LLM output."""

import json

import pytest

from app.services.resume_score import analyzer
from app.services.resume_score.models import MatchReport


def test_keyword_coverage_counts_jd_terms_present_in_resume():
    resume = "Built services in Python and Go on Kubernetes and PostgreSQL"
    jd = "We need Python, Go, Kubernetes, Kafka, Terraform and PostgreSQL experience"
    cov, matched, missing = analyzer.keyword_coverage(resume, jd)
    assert 40 <= cov <= 75
    assert "python" in matched and "kubernetes" in matched
    assert "kafka" in missing and "terraform" in missing


def test_keyword_coverage_empty_jd():
    assert analyzer.keyword_coverage("anything", "") == (0, [], [])


async def test_fallback_report_when_no_api_key(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr("app.services.resume_score.analyzer.get_settings", lambda: type("S", (), {"openai_api_key": None})())
    r = await analyzer.analyze("Python Kubernetes AWS", "Python Kubernetes AWS Kafka", ["experience", "skills"])
    get_settings.cache_clear()
    assert isinstance(r, MatchReport)
    assert r.keywords.coverage == r.overall_score
    assert r.dimensions and r.dimensions[0].key == "keywords"


class _Msg:
    def __init__(self, content):
        self.message = type("M", (), {"content": content})


class _Client:
    def __init__(self, content):
        async def create(**_):
            return type("R", (), {"choices": [_Msg(content)]})

        self.chat = type("C", (), {"completions": type("X", (), {"create": staticmethod(create)})})


async def test_analyze_blends_llm_output(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("OPENAI_API_KEY", "x")
    get_settings.cache_clear()

    payload = json.dumps(
        {
            "jd_title": "Senior Backend Engineer",
            "headline": "Solid fit",
            "summary": "Good overlap.",
            "dimensions": {"skills": 90, "experience": 80, "impact": 70, "seniority": 60, "education": 85},
            "dimension_notes": {"skills": "strong python"},
            "keywords_matched": ["Python", "Kubernetes"],
            "keywords_partial": ["Kafka"],
            "keywords_missing": ["Go", "Terraform"],
            "requirements": [
                {"requirement": "5+ yrs", "status": "partial", "evidence": "4 years"},
                {"requirement": "Go", "status": "missing", "evidence": ""},
                {"requirement": "bad", "status": "weird"},
            ],
            "strengths": ["python"],
            "gaps": ["go"],
            "suggestions": [
                {"section": "skills", "title": "Add Go", "detail": "mention Go", "priority": "high"},
                {"section": "not-a-real-section", "title": "x", "priority": "banana"},
            ],
        }
    )
    monkeypatch.setattr(analyzer, "AsyncOpenAI", lambda **_: _Client(payload))

    r = await analyzer.analyze("Python Kubernetes", "Python Go Kubernetes Kafka Terraform", ["skills", "experience"])
    get_settings.cache_clear()

    assert r.jd_title == "Senior Backend Engineer"
    assert 0 <= r.overall_score <= 100
    # keyword dimension mirrors the computed coverage
    kw_dim = next(d for d in r.dimensions if d.key == "keywords")
    assert kw_dim.score == r.keywords.coverage
    # bad requirement status normalised, bad suggestion section cleared, bad priority defaulted
    assert all(req.status in {"met", "partial", "missing"} for req in r.requirements)
    assert r.suggestions[1].section == ""
    assert r.suggestions[1].priority == "medium"
