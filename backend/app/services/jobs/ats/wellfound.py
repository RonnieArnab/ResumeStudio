"""Wellfound (AngelList Talent) discovery via a connected browser session.

Wellfound has no usable anonymous API and gates search behind login, so this
drives the user's connected session (see `apply/connected.py`) and scrapes the
rendered results. Best-effort: markup changes will break it, and it returns an
empty list rather than raising when it can't find cards.
"""

from __future__ import annotations

import asyncio
from urllib.parse import quote_plus

from app.services.jobs.apply.connected import close_connected_context, connected_context
from app.services.jobs.models import JobPosting

_MAX_CARDS = 40

_SCRAPE_JS = r"""
() => {
  const out = [];
  const anchors = Array.from(document.querySelectorAll('a[href*="/jobs/"]'));
  const seen = new Set();
  for (const a of anchors) {
    const m = a.getAttribute('href').match(/\/jobs\/(\d+)/);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    const card = a.closest('[class*="styles_component"], [data-test], li, div');
    const text = (card ? card.innerText : a.innerText || '').replace(/\s+/g, ' ').trim();
    out.push({
      id,
      href: a.href.split('?')[0],
      title: (a.innerText || '').replace(/\s+/g, ' ').trim(),
      cardText: text.slice(0, 400),
    });
  }
  return out;
}
"""


async def fetch_search_connected(query: str, location: str, id_prefix: str) -> list[JobPosting]:
    context = await connected_context("wellfound", headless=True)
    try:
        page = await context.new_page()
        url = f"https://wellfound.com/jobs?q={quote_plus(query)}"
        if location:
            url += f"&l={quote_plus(location)}"
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3500)

        if "/login" in page.url:
            from app.services.jobs.apply.connected import NeedsReconnect

            raise NeedsReconnect("Wellfound session expired — reconnect your account")

        raw = await page.evaluate(_SCRAPE_JS)
        postings: list[JobPosting] = []
        for item in raw[:_MAX_CARDS]:
            company = ""
            title = item["title"]
            parts = [p.strip() for p in item["cardText"].split("·") if p.strip()]
            if len(parts) >= 2:
                company = parts[0]
            postings.append(
                JobPosting(
                    id=f"{id_prefix}:{item['id']}",
                    provider="wellfound",
                    company=company or "",
                    title=title or item["cardText"][:80],
                    location=location,
                    remote="remote" in item["cardText"].lower(),
                    url=item["href"],
                    apply_url=item["href"],
                    description_text=item["cardText"],
                )
            )
            await asyncio.sleep(0)
        return postings
    finally:
        await close_connected_context(context)
