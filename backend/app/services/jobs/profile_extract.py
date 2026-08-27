"""Extract an applicant profile from resume text with one LLM call, so the user
doesn't have to type it in after uploading a resume."""

from __future__ import annotations

import json
import re

from openai import AsyncOpenAI

from app.config import get_settings
from app.services.jobs.models import ApplicantProfile

MODEL = "gpt-4o-mini"

_SYSTEM = """You extract structured contact/identity details from a resume. \
Return ONLY facts stated in the resume. Respond as JSON with these keys \
(use "" or null when the resume doesn't say):
- full_name
- email
- phone            (digits, spaces, +, -, () only)
- location         ("City, Country" or "City, State")
- linkedin_url     (ONLY if a linkedin.com/in/... URL literally appears; else "")
- github_url       (ONLY if a github.com/... URL literally appears; else "")
- portfolio_url    (personal site / portfolio, not github/linkedin; ONLY if a URL appears)
- years_experience (a number or short range as a string, e.g. "6" or "3-4"; estimate from work history dates if not stated)
- work_authorization (only if explicitly stated, e.g. "US citizen", "requires H1B sponsorship"; else "")
"""

_URL_RE = re.compile(r"https?://[^\s)]+", re.I)
_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:[\w.]*\.)?linkedin\.com/in/[\w\-%]+", re.I)
_GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+", re.I)
_EMAIL_RE = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")


def _regex_fallback(text: str) -> dict:
    out: dict = {}
    if m := _EMAIL_RE.search(text):
        out["email"] = m.group(0)
    if m := _LINKEDIN_RE.search(text):
        out["linkedin_url"] = m.group(0) if m.group(0).startswith("http") else f"https://{m.group(0)}"
    if m := _GITHUB_RE.search(text):
        out["github_url"] = m.group(0) if m.group(0).startswith("http") else f"https://{m.group(0)}"
    return out


def _strip_latex_comments(latex: str) -> str:
    # drop whole comment lines + the preamble (before \begin{document})
    body = latex.split("\\begin{document}", 1)[-1]
    return "\n".join(line for line in body.splitlines() if not line.lstrip().startswith("%"))


async def extract_profile_fields(resume_text: str, raw_latex: str = "") -> dict:
    """Best-effort dict of profile fields. Regex fallback if the LLM is off.
    `raw_latex` (if given) is also regex-scanned for URLs the plain text lost."""
    fallback = dict(_regex_fallback(resume_text))
    if raw_latex:
        for k, v in _regex_fallback(_strip_latex_comments(raw_latex)).items():
            fallback.setdefault(k, v)
    settings = get_settings()
    if not settings.openai_api_key:
        return fallback

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": resume_text[:8000]},
            ],
        )
        data = json.loads(resp.choices[0].message.content or "{}")
    except Exception:  # noqa: BLE001
        return fallback

    merged = {**fallback}
    haystack = (resume_text + " " + _strip_latex_comments(raw_latex)).lower()
    for k, v in data.items():
        val = str(v).strip()
        if not val or val.lower() in {"null", "none", "n/a"}:
            continue
        # never trust an LLM-invented URL — the handle must appear in the resume
        if k in {"linkedin_url", "github_url", "portfolio_url"}:
            handle = val.rstrip("/").rsplit("/", 1)[-1].lower()
            if handle and handle not in haystack:
                continue
        merged[k] = val
    return merged


def apply_extracted(profile: ApplicantProfile, fields: dict, *, overwrite: bool = False) -> ApplicantProfile:
    """Fill blank profile fields from an extraction (or overwrite all)."""
    keys = [
        "full_name", "email", "phone", "location",
        "linkedin_url", "github_url", "portfolio_url",
        "years_experience", "work_authorization",
    ]
    for key in keys:
        val = str(fields.get(key) or "").strip()
        if not val:
            continue
        if overwrite or not (getattr(profile, key, "") or "").strip():
            setattr(profile, key, val)
    return profile
