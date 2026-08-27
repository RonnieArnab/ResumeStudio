"""A small curated map of well-known companies to their ATS board, so the UI
can offer a searchable picker instead of making the user hunt for board URLs.

Seed data lives in `data/company_registry.json` — verified against the live
board APIs at build time, but boards do move, so a stale entry just yields a
`board_error` on crawl."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.services.jobs.models import RegistryEntry

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "company_registry.json"


@lru_cache
def _entries() -> list[RegistryEntry]:
    raw = json.loads(_REGISTRY_PATH.read_text())
    return [RegistryEntry(**e) for e in raw]


def search_registry(query: str, limit: int = 20) -> list[RegistryEntry]:
    entries = _entries()
    q = query.strip().lower()
    if not q:
        return sorted(entries, key=lambda e: e.name)[:limit]
    starts = [e for e in entries if e.name.lower().startswith(q)]
    contains = [e for e in entries if q in e.name.lower() and e not in starts]
    return (starts + contains)[:limit]
