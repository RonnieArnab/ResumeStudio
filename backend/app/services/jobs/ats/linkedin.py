"""LinkedIn job discovery via the public "guest" endpoints (no login).

These are the same endpoints LinkedIn's logged-out job search page calls. They
are UNOFFICIAL: undocumented, IP-rate-limited, and the markup can change without
notice. Automated applying is not done here (LinkedIn's terms prohibit it) — the
apply step opens Easy Apply in the user's connected browser and stops.
"""

from __future__ import annotations

import asyncio
import re

import httpx

from app.services.jobs.ats._util import html_to_text, parse_iso_dt
from app.services.jobs.models import JobPosting

_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
_POSTING_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_PER_PAGE = 25
_MAX_PAGES = 3
_JD_FETCH_CAP = 40

_CARD_RE = re.compile(r'data-entity-urn="urn:li:jobPosting:(\d+)"(.*?)(?=data-entity-urn="urn:li:jobPosting:|\Z)', re.S)
_TITLE_RE = re.compile(r'base-search-card__title">\s*(.*?)\s*</h3>', re.S)
_COMPANY_RE = re.compile(r'base-search-card__subtitle">.*?>\s*(.*?)\s*</a>', re.S)
_LOCATION_RE = re.compile(r'job-search-card__location">\s*(.*?)\s*</span>', re.S)
_DATE_RE = re.compile(r'<time[^>]*datetime="([^"]+)"')
_MARKUP_RE = re.compile(r'show-more-less-html__markup[^"]*">(.*?)</div>', re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return _TAG_RE.sub("", text).replace("&amp;", "&").strip()


async def _fetch_jd(job_id: str, client: httpx.AsyncClient) -> str:
    try:
        resp = await client.get(_POSTING_URL.format(job_id=job_id), headers={"User-Agent": _UA})
        if resp.status_code != 200:
            return ""
        match = _MARKUP_RE.search(resp.text)
        return html_to_text(match.group(1)) if match else ""
    except httpx.HTTPError:
        return ""


async def fetch_search(query: str, location: str, id_prefix: str, client: httpx.AsyncClient) -> list[JobPosting]:
    postings: list[JobPosting] = []
    seen: set[str] = set()
    jd_fetched = 0

    for page in range(_MAX_PAGES):
        try:
            resp = await client.get(
                _SEARCH_URL,
                params={"keywords": query, "location": location or "", "start": page * _PER_PAGE},
                headers={"User-Agent": _UA},
            )
        except httpx.HTTPError:
            break
        if resp.status_code in (429, 999) or resp.status_code >= 400:
            break

        cards = _CARD_RE.findall(resp.text)
        if not cards:
            break

        for job_id, body in cards:
            if job_id in seen:
                continue
            seen.add(job_id)
            title = _TITLE_RE.search(body)
            company = _COMPANY_RE.search(body)
            loc = _LOCATION_RE.search(body)
            date = _DATE_RE.search(body)

            description = ""
            if jd_fetched < _JD_FETCH_CAP:
                description = await _fetch_jd(job_id, client)
                jd_fetched += 1
                await asyncio.sleep(0.4)

            postings.append(
                JobPosting(
                    id=f"{id_prefix}:{job_id}",
                    provider="linkedin",
                    company=_clean(company.group(1)) if company else "",
                    title=_clean(title.group(1)) if title else "",
                    location=_clean(loc.group(1)) if loc else "",
                    remote="remote" in (loc.group(1).lower() if loc else ""),
                    url=f"https://www.linkedin.com/jobs/view/{job_id}",
                    apply_url=f"https://www.linkedin.com/jobs/view/{job_id}",
                    description_text=description,
                    posted_at=parse_iso_dt(date.group(1)) if date else None,
                )
            )

        await asyncio.sleep(1.5)

    return postings
