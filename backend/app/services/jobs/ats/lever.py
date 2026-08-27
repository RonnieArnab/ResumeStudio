"""Lever public postings API.

Docs: https://github.com/lever/postings-api
  GET https://api.lever.co/v0/postings/{slug}?mode=json
"""

from __future__ import annotations

import httpx

from app.services.jobs.ats._util import html_to_text, parse_epoch_ms
from app.services.jobs.models import JobPosting

_BASE = "https://api.lever.co/v0/postings"


async def fetch_postings(slug: str, client: httpx.AsyncClient) -> list[JobPosting]:
    resp = await client.get(f"{_BASE}/{slug}", params={"mode": "json"})
    resp.raise_for_status()
    payload = resp.json()

    postings: list[JobPosting] = []
    for job in payload:
        external_id = str(job.get("id"))
        categories = job.get("categories") or {}
        location = categories.get("location", "") or ""
        commitment = categories.get("commitment", "") or ""
        hosted_url = job.get("hostedUrl", "") or ""
        # `descriptionPlain` is already stripped; fall back to the HTML body.
        description = job.get("descriptionPlain") or html_to_text(job.get("description", ""))
        postings.append(
            JobPosting(
                id=f"lever:{slug}:{external_id}",
                provider="lever",
                company=slug,
                title=job.get("text", "") or "",
                location=location,
                team=categories.get("team") or categories.get("department"),
                remote="remote" in f"{location} {commitment}".lower(),
                url=hosted_url,
                apply_url=job.get("applyUrl") or (f"{hosted_url}/apply" if hosted_url else ""),
                description_text=description,
                posted_at=parse_epoch_ms(job.get("createdAt")),
            )
        )
    return postings
