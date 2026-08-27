"""Crawl orchestrator: fetch every posting from every configured source, score
each against the resume, and stream progress as SSE events (consumed by
`routes/jobs.py` via `services/agent/streaming.format_sse`).

Source kinds:
  - board  → Greenhouse/Lever/Ashby slug, fetched over HTTP
  - search → LinkedIn (HTTP guest API) or Wellfound (connected browser)
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.services.jobs.ats import fetch_postings, fetch_search
from app.services.jobs.crawl_store import crawl_store
from app.services.jobs.matcher import keyword_overlap, score_job
from app.services.jobs.models import BoardSource, JobPosting, MatchResult

_USER_AGENT = "resume-editor-agent/job-crawler (public job-board APIs)"
_MIN_KEYWORD_OVERLAP = 0.10
_MAX_SCORED_JOBS = 80  # guardrail against very large boards


async def _fetch_source(
    source: BoardSource,
    client: httpx.AsyncClient,
    *,
    posted_within_days: int | None,
    target_years_experience: int | None,
) -> list[JobPosting]:
    if source.kind == "search":
        if source.provider == "wellfound":
            from app.services.jobs.ats.wellfound import fetch_search_connected

            return await fetch_search_connected(source.query, source.location, source.key)
        return await fetch_search(
            source.provider,
            source.query,
            source.location,
            source.key,
            client,
            posted_within_days=posted_within_days,
            target_years_experience=target_years_experience,
        )
    return await fetch_postings(source.provider, source.slug, client)


def _too_old(job: JobPosting, cutoff: datetime | None) -> bool:
    if cutoff is None or job.posted_at is None:
        return False
    posted = job.posted_at
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
    return posted < cutoff


async def run_crawl(
    resume_text: str | None,
    *,
    posted_within_days: int | None = None,
    target_years_experience: int | None = None,
) -> AsyncIterator[dict[str, Any]]:
    sources = crawl_store.list_sources()
    if not sources:
        yield {"type": "done", "jobs": 0, "scored": 0, "message": "No sources configured yet."}
        return

    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=posted_within_days) if posted_within_days else None
    )
    total_jobs = 0
    scored = 0

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0), headers={"User-Agent": _USER_AGENT}, follow_redirects=True
    ) as client:
        for source in sources:
            yield {"type": "board_started", "provider": source.provider, "slug": source.label, "label": source.label}
            try:
                jobs = await _fetch_source(
                    source,
                    client,
                    posted_within_days=posted_within_days,
                    target_years_experience=target_years_experience,
                )
            except Exception as exc:  # noqa: BLE001 - one bad source shouldn't kill the crawl
                yield {"type": "board_error", "slug": source.label, "error": str(exc)}
                continue

            if cutoff is not None:
                fresh = [j for j in jobs if not _too_old(j, cutoff)]
                dropped = len(jobs) - len(fresh)
                jobs = fresh
                if dropped:
                    yield {"type": "filtered", "slug": source.label, "dropped_old": dropped}

            crawl_store.replace_jobs_for_source(source, jobs)
            total_jobs += len(jobs)
            yield {"type": "jobs_found", "slug": source.label, "count": len(jobs)}

            if not resume_text:
                continue

            for job in jobs:
                if keyword_overlap(resume_text, job) < _MIN_KEYWORD_OVERLAP:
                    crawl_store.set_match(
                        MatchResult(
                            job_id=job.id,
                            score=0,
                            verdict="weak",
                            summary="Skipped detailed scoring — little vocabulary overlap with your resume.",
                        )
                    )
                    yield {"type": "job_scored", "job_id": job.id, "title": job.title, "score": 0, "skipped": True}
                    continue

                if scored >= _MAX_SCORED_JOBS:
                    yield {"type": "job_scored", "job_id": job.id, "title": job.title, "score": None, "capped": True}
                    continue

                match = await score_job(resume_text, job, target_years_experience=target_years_experience)
                crawl_store.set_match(match)
                scored += 1
                yield {
                    "type": "job_scored",
                    "job_id": job.id,
                    "title": job.title,
                    "score": match.score,
                    "verdict": match.verdict,
                }

            await asyncio.sleep(0.4)  # politeness between sources

    yield {"type": "done", "jobs": total_jobs, "scored": scored}
