"""Greenhouse public job-board API.

Docs: https://developers.greenhouse.io/job-board.html
  GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
  GET https://boards-api.greenhouse.io/v1/boards/{slug}   -> { "name": ... }
"""

from __future__ import annotations

import httpx

from app.services.jobs.ats._util import html_to_text, parse_iso_dt
from app.services.jobs.models import JobPosting

_BASE = "https://boards-api.greenhouse.io/v1/boards"


async def _company_name(slug: str, client: httpx.AsyncClient) -> str:
    try:
        resp = await client.get(f"{_BASE}/{slug}")
        resp.raise_for_status()
        return resp.json().get("name") or slug
    except (httpx.HTTPError, ValueError):
        return slug


async def fetch_postings(slug: str, client: httpx.AsyncClient) -> list[JobPosting]:
    resp = await client.get(f"{_BASE}/{slug}/jobs", params={"content": "true"})
    resp.raise_for_status()
    payload = resp.json()
    company = await _company_name(slug, client)

    postings: list[JobPosting] = []
    for job in payload.get("jobs", []):
        external_id = str(job.get("id"))
        location = (job.get("location") or {}).get("name", "") or ""
        departments = [d.get("name") for d in job.get("departments", []) if d.get("name")]
        absolute_url = job.get("absolute_url", "") or ""
        # `absolute_url` sometimes points at a company-hosted careers page that
        # only *links* to the form. Prefer it when it's already a Greenhouse
        # host (form is embedded there); otherwise fall back to the hosted
        # board URL as the best guess for a fillable page.
        if "greenhouse.io" in absolute_url:
            hosted_apply_url = absolute_url
        else:
            hosted_apply_url = f"https://job-boards.greenhouse.io/{slug}/jobs/{external_id}"
        postings.append(
            JobPosting(
                id=f"greenhouse:{slug}:{external_id}",
                provider="greenhouse",
                company=company,
                title=job.get("title", "") or "",
                location=location,
                team=departments[0] if departments else None,
                remote="remote" in location.lower(),
                url=absolute_url or hosted_apply_url,
                apply_url=hosted_apply_url,
                description_text=html_to_text(job.get("content", "")),
                posted_at=parse_iso_dt(job.get("updated_at") or job.get("first_published")),
            )
        )
    return postings
