"""Score a job posting against the user's resume with a single LLM call.

Reuses the OpenAI setup from `services/agent/orchestrator.py` (same client,
same `gpt-4o-mini` model)."""

from __future__ import annotations

import json
import re

from openai import AsyncOpenAI

from app.config import get_settings
from app.services.jobs.models import JobPosting, MatchResult

MODEL = "gpt-4o-mini"

_SYSTEM_PROMPT = """You are a pragmatic technical recruiter. Given a candidate's \
resume and a job posting, judge how good a match the candidate is for THIS role.

Return a JSON object with exactly these keys:
- "score": integer 0-100. 0-40 weak, 41-70 possible, 71-100 strong.
- "verdict": one of "strong", "possible", "weak".
- "summary": one or two sentences on the fit, addressed to the candidate.
- "matched_requirements": array of short strings — role requirements the resume clearly satisfies.
- "missing_requirements": array of short strings — requirements the resume does not evidence.

Judge on skills, seniority, domain, and hard constraints (location, work \
authorization if stated). Be honest; do not inflate the score."""

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.]{2,}")

_STOPWORDS = {
    "the", "and", "for", "with", "you", "our", "are", "will", "your", "this", "that", "have",
    "from", "not", "all", "who", "can", "has", "was", "job", "role", "team", "work", "working",
    "company", "years", "year", "experience", "including", "such", "other", "must", "should",
}


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)} - _STOPWORDS


def keyword_overlap(resume_text: str, job: JobPosting) -> float:
    """Fraction of the resume's vocabulary that also appears in the posting.
    Used only to skip obviously unrelated roles before spending an LLM call —
    kept lenient so borderline matches still get scored properly."""
    resume_tokens = _tokens(resume_text)
    if not resume_tokens:
        return 1.0  # no resume vocabulary to filter on — score everything
    jd_tokens = _tokens(f"{job.title} {job.title} {job.description_text}")
    return len(resume_tokens & jd_tokens) / len(resume_tokens)


async def score_job(resume_text: str, job: JobPosting) -> MatchResult:
    settings = get_settings()
    if not settings.openai_api_key:
        return MatchResult(job_id=job.id, verdict="error", summary="OPENAI_API_KEY is not set", error="missing_api_key")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    user_prompt = (
        f"RESUME:\n{resume_text[:6000]}\n\n"
        f"JOB TITLE: {job.title}\n"
        f"COMPANY: {job.company}\n"
        f"LOCATION: {job.location or 'unspecified'}\n"
        f"REMOTE: {job.remote}\n\n"
        f"JOB DESCRIPTION:\n{job.description_text[:6000]}"
    )

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        data = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:  # noqa: BLE001 - a bad score shouldn't abort the whole crawl
        return MatchResult(job_id=job.id, verdict="error", summary="Scoring failed", error=str(exc))

    score = data.get("score", 0)
    try:
        score = max(0, min(100, int(score)))
    except (TypeError, ValueError):
        score = 0

    verdict = str(data.get("verdict") or "").lower()
    if verdict not in {"strong", "possible", "weak"}:
        verdict = "strong" if score >= 71 else "possible" if score >= 41 else "weak"

    def _str_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(v).strip() for v in value if str(v).strip()][:10]

    return MatchResult(
        job_id=job.id,
        score=score,
        verdict=verdict,
        summary=str(data.get("summary") or "").strip(),
        matched_requirements=_str_list(data.get("matched_requirements")),
        missing_requirements=_str_list(data.get("missing_requirements")),
    )
