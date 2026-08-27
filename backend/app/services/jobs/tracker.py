"""Applied-jobs tracker.

A lightweight application log persisted to `.data/jobs/applications.json` (like
the profile — survives restarts). Entries are upserted by `job_id` so preparing
then submitting the same job updates one row."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from app.services.jobs.storage import JOBS_DIR

APPLICATIONS_PATH = JOBS_DIR / "applications.json"

TrackerStatus = Literal[
    "interested", "preparing", "applied", "interviewing", "offer", "rejected", "withdrawn"
]

STATUS_ORDER: list[str] = ["interested", "preparing", "applied", "interviewing", "offer", "rejected", "withdrawn"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Application(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str | None = None
    company: str = ""
    title: str = ""
    url: str = ""
    provider: str = ""
    source: str = "manual"  # manual | apply | submit
    status: TrackerStatus = "applied"
    notes: str = ""
    applied_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class ApplicationCreate(BaseModel):
    company: str = ""
    title: str = ""
    url: str = ""
    provider: str = ""
    status: TrackerStatus = "applied"
    notes: str = ""


class ApplicationUpdate(BaseModel):
    status: TrackerStatus | None = None
    notes: str | None = None
    company: str | None = None
    title: str | None = None


def _load() -> list[Application]:
    if not APPLICATIONS_PATH.exists():
        return []
    try:
        return [Application(**row) for row in json.loads(APPLICATIONS_PATH.read_text())]
    except (ValueError, OSError):
        return []


def _save(apps: list[Application]) -> None:
    APPLICATIONS_PATH.write_text(json.dumps([json.loads(a.model_dump_json()) for a in apps], indent=2))


def list_applications() -> list[Application]:
    return sorted(_load(), key=lambda a: a.updated_at, reverse=True)


def add_application(data: ApplicationCreate) -> Application:
    apps = _load()
    app = Application(**data.model_dump())
    apps.append(app)
    _save(apps)
    return app


def update_application(app_id: str, data: ApplicationUpdate) -> Application | None:
    apps = _load()
    for app in apps:
        if app.id == app_id:
            for k, v in data.model_dump(exclude_none=True).items():
                setattr(app, k, v)
            app.updated_at = _now()
            _save(apps)
            return app
    return None


def delete_application(app_id: str) -> bool:
    apps = _load()
    remaining = [a for a in apps if a.id != app_id]
    if len(remaining) == len(apps):
        return False
    _save(remaining)
    return True


def record_apply(job, *, status: TrackerStatus, source: str, notes: str = "") -> Application:
    """Upsert a tracker row for an apply run. `job` is a JobPosting-like object."""
    apps = _load()
    for app in apps:
        if app.job_id and app.job_id == job.id:
            # Don't downgrade a manually-advanced status back to 'preparing'.
            if not (status == "preparing" and STATUS_ORDER.index(app.status) > STATUS_ORDER.index("preparing")):
                app.status = status
            app.updated_at = _now()
            if notes:
                app.notes = notes
            _save(apps)
            return app

    app = Application(
        job_id=job.id,
        company=getattr(job, "company", "") or "",
        title=getattr(job, "title", "") or "",
        url=getattr(job, "url", "") or getattr(job, "apply_url", "") or "",
        provider=getattr(job, "provider", "") or "",
        source=source,
        status=status,
        notes=notes,
    )
    apps.append(app)
    _save(apps)
    return app
