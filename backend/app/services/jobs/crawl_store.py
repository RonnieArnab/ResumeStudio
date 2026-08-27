"""In-memory state for the job feature: board sources, discovered postings and
their match results, and live apply runs. Mirrors `session/session_store.py`
— deliberately small so it can move to Redis later."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.services.jobs.models import (
    ApplyRun,
    BoardSource,
    JobPosting,
    MatchResult,
    Provider,
    RankedJob,
)


class CrawlStore:
    def __init__(self) -> None:
        self._sources: dict[str, BoardSource] = {}
        self._jobs: dict[str, JobPosting] = {}
        self._matches: dict[str, MatchResult] = {}
        self._runs: dict[str, ApplyRun] = {}

    # ---- sources ---------------------------------------------------------- #

    def list_sources(self) -> list[BoardSource]:
        return sorted(self._sources.values(), key=lambda s: s.added_at)

    def add_board_source(self, provider: Provider, slug: str, label: str | None) -> BoardSource:
        for existing in self._sources.values():
            if existing.kind == "board" and existing.provider == provider and existing.slug == slug:
                return existing
        source = BoardSource(
            id=str(uuid.uuid4()),
            provider=provider,
            kind="board",
            slug=slug,
            label=label or slug,
            added_at=datetime.now(timezone.utc),
        )
        self._sources[source.id] = source
        return source

    def add_search_source(self, provider: Provider, query: str, location: str, label: str | None) -> BoardSource:
        for existing in self._sources.values():
            if (
                existing.kind == "search"
                and existing.provider == provider
                and existing.query == query
                and existing.location == location
            ):
                return existing
        source = BoardSource(
            id=str(uuid.uuid4()),
            provider=provider,
            kind="search",
            query=query,
            location=location,
            label=label or (f"{query} · {location}" if location else query),
            added_at=datetime.now(timezone.utc),
        )
        self._sources[source.id] = source
        return source

    def get_source(self, source_id: str) -> BoardSource | None:
        return self._sources.get(source_id)

    def remove_source(self, source_id: str) -> bool:
        return self._sources.pop(source_id, None) is not None

    # ---- jobs + matches ------------------------------------------------- #

    def replace_jobs_for_source(self, source: BoardSource, jobs: list[JobPosting]) -> None:
        prefix = f"{source.key}:"
        for job_id in [jid for jid in self._jobs if jid.startswith(prefix)]:
            self._jobs.pop(job_id, None)
            self._matches.pop(job_id, None)
        for job in jobs:
            self._jobs[job.id] = job

    def upsert_job(self, job: JobPosting) -> None:
        self._jobs[job.id] = job

    def set_match(self, match: MatchResult) -> None:
        self._matches[match.job_id] = match

    def get_job(self, job_id: str) -> JobPosting | None:
        return self._jobs.get(job_id)

    def get_match(self, job_id: str) -> MatchResult | None:
        return self._matches.get(job_id)

    def ranked_jobs(
        self,
        min_score: int = 0,
        location_contains: str | None = None,
        provider: Provider | None = None,
        remote_only: bool = False,
        posted_within_days: int | None = None,
    ) -> list[RankedJob]:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=posted_within_days) if posted_within_days else None

        def age_days(job) -> float | None:
            if job.posted_at is None:
                return None
            posted = job.posted_at if job.posted_at.tzinfo else job.posted_at.replace(tzinfo=timezone.utc)
            return (now - posted).total_seconds() / 86400

        def recency_boost(job) -> int:
            d = age_days(job)
            if d is None:
                return 0
            if d <= 1:
                return 10
            if d <= 3:
                return 6
            if d <= 7:
                return 3
            return 0

        rows: list[RankedJob] = []
        for job in self._jobs.values():
            if provider and job.provider != provider:
                continue
            if remote_only and not job.remote:
                continue
            if location_contains and location_contains.lower() not in job.location.lower():
                continue
            d = age_days(job)
            if cutoff is not None and d is not None and job.posted_at and job.posted_at.replace(tzinfo=job.posted_at.tzinfo or timezone.utc) < cutoff:
                continue
            match = self._matches.get(job.id)
            if match and match.score < min_score:
                continue
            rows.append(RankedJob(job=job, match=match))

        # rank by score, then a freshness boost, then raw recency
        rows.sort(
            key=lambda r: (
                (r.match.score if r.match else -1) + recency_boost(r.job),
                -(age_days(r.job) if age_days(r.job) is not None else 9999),
            ),
            reverse=True,
        )
        return rows

    # ---- apply runs ---------------------------------------------------- #

    def put_run(self, run: ApplyRun) -> None:
        self._runs[run.run_id] = run

    def get_run(self, run_id: str) -> ApplyRun | None:
        return self._runs.get(run_id)

    def drop_run(self, run_id: str) -> ApplyRun | None:
        return self._runs.pop(run_id, None)

    def all_runs(self) -> list[ApplyRun]:
        return list(self._runs.values())


crawl_store = CrawlStore()
