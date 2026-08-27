"""Playwright lifecycle for the apply flow.

One lazily-launched headless Chromium is shared across runs; each run gets its
own browser context (isolated cookies/storage). Live pages are held on the
`ApplyRun` in `crawl_store` so `prepare` and a later `submit` — separate HTTP
requests — operate on the same page. Abandoned runs are swept on a TTL."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from app.services.jobs.crawl_store import crawl_store

RUN_TTL = timedelta(minutes=20)

_playwright = None
_browser = None
_lock = asyncio.Lock()


async def get_browser():
    global _playwright, _browser
    async with _lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        from playwright.async_api import async_playwright

        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        return _browser


async def new_context():
    browser = await get_browser()
    return await browser.new_context(
        viewport={"width": 1280, "height": 1600},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
    )


async def close_run_browser(run) -> None:
    context = getattr(run, "context", None)
    if context is not None:
        # Connected (LinkedIn/Wellfound) contexts own their own Playwright +
        # Browser and need a fuller teardown.
        if hasattr(context, "_owned_browser"):
            from app.services.jobs.apply.connected import close_connected_context

            try:
                await close_connected_context(context)
            except Exception:  # noqa: BLE001
                pass
        else:
            try:
                await context.close()
            except Exception:  # noqa: BLE001 - best effort teardown
                pass
    run.page = None
    run.context = None


async def sweep_stale_runs() -> None:
    cutoff = datetime.now(timezone.utc) - RUN_TTL
    for run in crawl_store.all_runs():
        if run.status in {"submitted", "cancelled", "failed"} or run.updated_at < cutoff:
            await close_run_browser(run)
            if run.updated_at < cutoff and run.status not in {"submitted"}:
                run.status = "cancelled"
            crawl_store.drop_run(run.run_id)


async def shutdown() -> None:
    global _playwright, _browser
    for run in crawl_store.all_runs():
        await close_run_browser(run)
    if _browser is not None:
        try:
            await _browser.close()
        finally:
            _browser = None
    if _playwright is not None:
        try:
            await _playwright.stop()
        finally:
            _playwright = None
