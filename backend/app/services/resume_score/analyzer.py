"""Rate a resume against a specific job description and return detailed metrics.

One `gpt-4o-mini` call for the qualitative analysis; the keyword coverage and the
headline number are computed deterministically from its output so the metrics and
the score always agree. Degrades to a keyword-only report with no API key."""

from __future__ import annotations

import json
import re

from openai import AsyncOpenAI

from app.config import get_settings
from app.services.resume_score.models import (
    KeywordAnalysis,
    MatchReport,
    RequirementMatch,
    ScoreDimension,
    Suggestion,
)

MODEL = "gpt-4o-mini"

# key -> (label, weight). "keywords" is filled from the deterministic coverage.
_DIMENSIONS: list[tuple[str, str, float]] = [
    ("skills", "Skills & tools", 0.27),
    ("experience", "Relevant experience", 0.27),
    ("keywords", "Keyword / ATS coverage", 0.16),
    ("impact", "Quantified impact", 0.13),
    ("seniority", "Seniority fit", 0.12),
    ("education", "Education & certifications", 0.05),
]

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#./-]{1,}")
_STOP = {
    "the", "and", "for", "with", "you", "our", "are", "will", "your", "this", "that", "have",
    "from", "not", "all", "who", "can", "has", "was", "job", "role", "team", "work", "working",
    "company", "years", "year", "experience", "including", "such", "other", "must", "should",
    "we", "a", "an", "to", "in", "of", "or", "as", "is", "be", "on", "at", "by", "it", "its",
    "their", "they", "them", "about", "into", "across", "within", "using", "help", "build",
    "strong", "good", "great", "new", "well", "also", "etc", "per", "via",
}


def _norm_tokens(text: str) -> set[str]:
    return {t.lower().strip("./-") for t in _TOKEN_RE.findall(text)} - _STOP


def keyword_coverage(resume_text: str, jd_text: str) -> tuple[int, list[str], list[str]]:
    """Deterministic: which JD terms show up in the resume. Returns
    (coverage_pct, matched_sample, missing_sample)."""
    jd = _norm_tokens(jd_text)
    jd = {t for t in jd if len(t) >= 3}
    if not jd:
        return 0, [], []
    resume = _norm_tokens(resume_text)
    matched = sorted(jd & resume)
    missing = sorted(jd - resume)
    return round(100 * len(matched) / len(jd)), matched[:40], missing[:40]


def _fallback_report(resume_text: str, jd_text: str) -> MatchReport:
    cov, matched, missing = keyword_coverage(resume_text, jd_text)
    verdict = "strong" if cov >= 55 else "moderate" if cov >= 30 else "weak"
    return MatchReport(
        overall_score=cov,
        verdict=verdict,
        headline=f"{cov}% keyword overlap with the job description",
        summary="Detailed analysis needs an OpenAI API key — this is a keyword-only estimate.",
        dimensions=[ScoreDimension(key="keywords", label="Keyword / ATS coverage", score=cov, weight=1.0)],
        keywords=KeywordAnalysis(coverage=cov, matched=matched, missing=missing),
    )


_SYSTEM = """You are an expert technical recruiter and resume reviewer. Given a \
candidate's resume and ONE job description, produce a precise, honest gap analysis.

Return a JSON object with exactly these keys:
- "jd_title": the role title from the JD (short string).
- "headline": one punchy sentence summarising the fit, addressed to the candidate.
- "summary": 2-3 sentences of honest assessment.
- "dimensions": object mapping each of these keys to an integer 0-100 —
  "skills", "experience", "impact", "seniority", "education".
  (Do NOT include "keywords"; that is computed separately.)
- "dimension_notes": object mapping the same keys to a short (<= 12 word) reason for the score.
- "keywords_matched": array of important skills/tools/terms from the JD that the resume clearly demonstrates.
- "keywords_partial": array of JD terms the resume touches on but weakly.
- "keywords_missing": array of important JD terms absent from the resume.
- "requirements": array of up to 10 objects {"requirement": str, "status": "met"|"partial"|"missing", "evidence": str}
  covering the JD's stated must-haves/responsibilities. "evidence" quotes or paraphrases the resume line, or "" if missing.
- "strengths": array of up to 6 short strings — where the candidate is a strong fit.
- "gaps": array of up to 6 short strings — the most important weaknesses vs this JD.
- "suggestions": array of up to 6 objects {"section": str, "title": str, "detail": str, "priority": "high"|"medium"|"low"}
  — concrete resume edits to close the gaps. "section" MUST be one of the provided section ids, or "" if it doesn't map to one.

Be specific and grounded in the resume. Never invent experience the candidate doesn't have.
Scores of 90+ mean an obvious, near-perfect fit; be sparing with them."""


def _clamp(v: object, default: int = 0) -> int:
    try:
        return max(0, min(100, int(v)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _str_list(v: object, limit: int = 12) -> list[str]:
    if not isinstance(v, list):
        return []
    return [str(x).strip() for x in v if str(x).strip()][:limit]


async def analyze(resume_text: str, jd_text: str, section_ids: list[str]) -> MatchReport:
    settings = get_settings()
    cov, det_matched, det_missing = keyword_coverage(resume_text, jd_text)

    if not settings.openai_api_key:
        return _fallback_report(resume_text, jd_text)

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    user = (
        f"SECTION IDS (use these for suggestion.section): {section_ids}\n\n"
        f"RESUME:\n{resume_text[:8000]}\n\n"
        f"JOB DESCRIPTION:\n{jd_text[:8000]}"
    )
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
        )
        data = json.loads(resp.choices[0].message.content or "{}")
    except Exception:  # noqa: BLE001
        return _fallback_report(resume_text, jd_text)

    dims_in = data.get("dimensions") or {}
    notes_in = data.get("dimension_notes") or {}

    matched = _str_list(data.get("keywords_matched"), 40) or det_matched
    partial = _str_list(data.get("keywords_partial"), 20)
    missing = _str_list(data.get("keywords_missing"), 40) or det_missing
    total_kw = len(matched) + len(partial) + len(missing)
    kw_coverage = round(100 * (len(matched) + 0.5 * len(partial)) / total_kw) if total_kw else cov

    dimensions: list[ScoreDimension] = []
    weighted_sum = 0.0
    weight_total = 0.0
    for key, label, weight in _DIMENSIONS:
        score = kw_coverage if key == "keywords" else _clamp(dims_in.get(key), 0)
        note = "JD terms present in the resume" if key == "keywords" else str(notes_in.get(key) or "").strip()
        dimensions.append(ScoreDimension(key=key, label=label, score=score, weight=weight, note=note[:120]))
        weighted_sum += score * weight
        weight_total += weight

    overall = round(weighted_sum / weight_total) if weight_total else kw_coverage
    verdict = "strong" if overall >= 70 else "moderate" if overall >= 45 else "weak"

    requirements: list[RequirementMatch] = []
    for r in data.get("requirements") or []:
        if not isinstance(r, dict) or not str(r.get("requirement", "")).strip():
            continue
        status = str(r.get("status", "")).lower()
        if status not in {"met", "partial", "missing"}:
            status = "partial"
        requirements.append(
            RequirementMatch(
                requirement=str(r["requirement"]).strip()[:200],
                status=status,  # type: ignore[arg-type]
                evidence=str(r.get("evidence") or "").strip()[:240],
            )
        )

    suggestions: list[Suggestion] = []
    for s in data.get("suggestions") or []:
        if not isinstance(s, dict) or not str(s.get("title", "")).strip():
            continue
        section = str(s.get("section") or "").strip()
        if section and section not in section_ids:
            section = ""
        pr = str(s.get("priority", "")).lower()
        suggestions.append(
            Suggestion(
                section=section,
                title=str(s["title"]).strip()[:160],
                detail=str(s.get("detail") or "").strip()[:400],
                priority=pr if pr in {"high", "medium", "low"} else "medium",  # type: ignore[arg-type]
            )
        )

    return MatchReport(
        overall_score=overall,
        verdict=verdict,  # type: ignore[arg-type]
        headline=str(data.get("headline") or "").strip()[:200] or f"{overall}% match with this role",
        summary=str(data.get("summary") or "").strip()[:600],
        dimensions=dimensions,
        keywords=KeywordAnalysis(coverage=kw_coverage, matched=matched, partial=partial, missing=missing),
        requirements=requirements[:12],
        strengths=_str_list(data.get("strengths"), 6),
        gaps=_str_list(data.get("gaps"), 6),
        suggestions=suggestions[:6],
        jd_title=str(data.get("jd_title") or "").strip()[:120],
    )
