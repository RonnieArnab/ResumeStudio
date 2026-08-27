"""Ashby public job-board API.

Docs: https://developers.ashbyhq.com/docs/public-job-posting-api
  GET https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true
"""

from __future__ import annotations

import httpx

from app.services.jobs.ats._util import html_to_text, parse_iso_dt
from app.services.jobs.models import JobPosting

_BASE = "https://api.ashbyhq.com/posting-api/job-board"


async def fetch_postings(slug: str, client: httpx.AsyncClient) -> list[JobPosting]:
    resp = await client.get(f"{_BASE}/{slug}", params={"includeCompensation": "true"})
    resp.raise_for_status()
    payload = resp.json()

    postings: list[JobPosting] = []
    for job in payload.get("jobs", []):
        external_id = str(job.get("id"))
        job_url = job.get("jobUrl", "") or ""
        description = html_to_text(job.get("descriptionHtml", "")) or (job.get("descriptionPlain", "") or "")
        postings.append(
            JobPosting(
                id=f"ashby:{slug}:{external_id}",
                provider="ashby",
                company=job.get("organizationName") or slug,
                title=job.get("title", "") or "",
                location=job.get("location", "") or "",
                team=job.get("team") or job.get("department"),
                remote=bool(job.get("isRemote")),
                url=job_url,
                apply_url=job.get("applyUrl") or (f"{job_url}/application" if job_url else ""),
                description_text=description,
                posted_at=parse_iso_dt(job.get("publishedAt") or job.get("updatedAt")),
            )
        )
    return postings
