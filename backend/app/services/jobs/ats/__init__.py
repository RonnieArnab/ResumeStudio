"""ATS provider registry + board-reference parsing.

Discovery uses each provider's official public job-board JSON API — no HTML
scraping of listing pages. Playwright is only involved later, at apply time."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

import httpx

from app.services.jobs.ats import ashby, greenhouse, lever, linkedin
from app.services.jobs.models import JobPosting, Provider

FetchFn = Callable[[str, httpx.AsyncClient], Awaitable[list[JobPosting]]]

# Slug-based board APIs.
PROVIDERS: dict[Provider, FetchFn] = {
    "greenhouse": greenhouse.fetch_postings,
    "lever": lever.fetch_postings,
    "ashby": ashby.fetch_postings,
}

# Keyword/location search providers (no per-company slug).
SEARCH_PROVIDERS: tuple[Provider, ...] = ("linkedin", "wellfound")

_HOST_PROVIDER: dict[str, Provider] = {
    "boards.greenhouse.io": "greenhouse",
    "job-boards.greenhouse.io": "greenhouse",
    "boards-api.greenhouse.io": "greenhouse",
    "jobs.lever.co": "lever",
    "api.lever.co": "lever",
    "jobs.ashbyhq.com": "ashby",
    "api.ashbyhq.com": "ashby",
}


def parse_board_ref(ref: str) -> tuple[Provider, str]:
    """Accept a board URL ("boards.greenhouse.io/stripe", with or without
    scheme) or a "provider:slug" shorthand. Returns (provider, slug)."""
    ref = ref.strip()
    if not ref:
        raise ValueError("Empty board reference")

    looks_like_url = "://" in ref or "." in ref.split("/", 1)[0]
    if looks_like_url:
        parsed = urlparse(ref if "://" in ref else f"https://{ref}")
        host = parsed.netloc.lower().split(":")[0]
        provider = _HOST_PROVIDER.get(host)
        segments = [s for s in parsed.path.split("/") if s]
        if provider is None or not segments:
            raise ValueError(f"Unrecognized board URL: {ref}")
        return provider, segments[0]

    if ":" in ref:
        raw_provider, slug = ref.split(":", 1)
        raw_provider = raw_provider.strip().lower()
        if raw_provider not in PROVIDERS:
            raise ValueError(f"Unknown provider '{raw_provider}'. Supported: {', '.join(PROVIDERS)}")
        slug = slug.strip().strip("/")
        if not slug:
            raise ValueError("Missing board slug")
        return raw_provider, slug  # type: ignore[return-value]

    raise ValueError("Provide a board URL or 'provider:slug' (e.g. 'greenhouse:stripe')")


async def fetch_postings(provider: Provider, slug: str, client: httpx.AsyncClient) -> list[JobPosting]:
    return await PROVIDERS[provider](slug, client)


async def fetch_search(
    provider: Provider, query: str, location: str, id_prefix: str, client: httpx.AsyncClient
) -> list[JobPosting]:
    if provider == "linkedin":
        return await linkedin.fetch_search(query, location, id_prefix, client)
    raise ValueError(f"{provider} search is not available over HTTP (needs a connected browser)")
