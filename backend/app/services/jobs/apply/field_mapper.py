"""Decide a value for every extracted form field.

Two passes:
  1. Deterministic heuristics for the standard identity fields (name, email,
     phone, links, resume upload) — no LLM, no cost, no surprises.
  2. One LLM call for whatever is left (screening questions, free text,
     dropdowns), given the resume, the JD and the profile's canned answers.
"""

from __future__ import annotations

import json

from openai import AsyncOpenAI

from app.config import get_settings
from app.services.jobs.models import ApplicantProfile, FormField, JobPosting

MODEL = "gpt-4o-mini"

_HEURISTICS: list[tuple[tuple[str, ...], str]] = [
    (("first name", "given name", "forename"), "first_name"),
    (("last name", "surname", "family name"), "last_name"),
    (("full name", "your name", "legal name", "full legal name"), "full_name"),
    (("email",), "email"),
    (("phone", "mobile", "telephone"), "phone"),
    (("linkedin",), "linkedin_url"),
    (("github",), "github_url"),
    (("portfolio", "website", "personal site", "url"), "portfolio_url"),
    (("city", "location", "where are you based", "current location"), "location"),
    (("pronoun",), "pronouns"),
    (("years of experience", "years experience"), "years_experience"),
]


def _match_heuristic(label: str) -> str | None:
    low = label.lower().strip()
    if low == "name":
        return "full_name"
    for needles, attr in _HEURISTICS:
        if any(n in low for n in needles):
            return attr
    return None


def _canned_answer(label: str, profile: ApplicantProfile) -> str | None:
    low = label.lower()
    for keyword, answer in profile.default_answers.items():
        if keyword.lower() in low:
            return answer
    if "sponsor" in low and profile.requires_sponsorship is not None:
        return "Yes" if profile.requires_sponsorship else "No"
    if ("authorized to work" in low or "work authorization" in low) and profile.work_authorization:
        return profile.work_authorization
    return None


def apply_profile_heuristics(field: FormField, profile: ApplicantProfile) -> None:
    if field.kind == "file":
        if profile.resume_pdf_path:
            field.value = "resume.pdf"
            field.source = "profile"
        return

    # Identity heuristics only make sense for free-text inputs — a checkbox
    # labelled "Use name only" must not get the applicant's name typed in.
    if field.kind not in {"checkbox", "radio"}:
        attr = _match_heuristic(field.label)
        if attr:
            value = getattr(profile, attr, "") or ""
            if value:
                field.value = value
                field.source = "profile"
                return

    canned = _canned_answer(field.label, profile)
    if canned:
        field.value = canned
        field.source = "default"


_SYSTEM_PROMPT = """You fill out job application forms on behalf of a candidate. \
You are given the candidate's resume, profile facts, the job, and a list of \
unfilled fields. For each field return the exact text to enter.

Rules:
- Use only facts from the resume/profile. Never invent employers, dates, or numbers.
- For a <select> or radio field, return one of its listed options verbatim, or "" if none clearly fit.
- For yes/no eligibility questions, answer from the profile; if unknown, return "".
- For open-ended questions ("why do you want to work here", cover letter), write 2-4 concise, specific sentences grounded in the resume and JD.
- Return "" for anything you cannot answer responsibly.

Respond with JSON: {"fields": [{"selector": "...", "value": "...", "confident": true|false}]}"""


async def map_fields(
    fields: list[FormField],
    job: JobPosting,
    profile: ApplicantProfile,
    resume_text: str,
) -> list[FormField]:
    for field in fields:
        if field.source == "empty":
            apply_profile_heuristics(field, profile)

    unresolved = [
        f
        for f in fields
        if f.source == "empty" and f.kind in {"text", "email", "tel", "url", "number", "textarea", "select", "combobox", "radio"}
    ]
    settings = get_settings()
    if not unresolved or not settings.openai_api_key:
        return fields

    field_specs = [
        {"selector": f.selector, "label": f.label, "kind": f.kind, "options": f.options, "required": f.required}
        for f in unresolved
    ]
    profile_facts = profile.model_dump(
        include={
            "full_name", "email", "phone", "location", "linkedin_url", "github_url",
            "portfolio_url", "work_authorization", "requires_sponsorship", "years_experience",
            "pronouns", "cover_letter_blurb",
        }
    )
    user_prompt = (
        f"RESUME:\n{resume_text[:5000]}\n\n"
        f"PROFILE FACTS (JSON):\n{json.dumps(profile_facts)}\n\n"
        f"JOB: {job.title} at {job.company} ({job.location})\n"
        f"JOB DESCRIPTION:\n{job.description_text[:4000]}\n\n"
        f"FIELDS TO FILL (JSON):\n{json.dumps(field_specs)}"
    )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
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
    except Exception:  # noqa: BLE001 - fall back to leaving fields blank for the user
        return fields

    by_selector = {f.selector: f for f in unresolved}
    for entry in data.get("fields", []):
        target = by_selector.get(entry.get("selector"))
        value = str(entry.get("value") or "").strip()
        if not target or not value:
            continue
        if target.kind in {"select", "radio"} and value not in target.options:
            match = next((o for o in target.options if o.lower() == value.lower()), None)
            if match is None:
                continue
            value = match
        target.value = value
        target.source = "generated"

    return fields
