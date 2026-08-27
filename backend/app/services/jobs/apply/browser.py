"""Playwright lifecycle for the apply flow.

- ATS boards (Greenhouse/Lever/Ashby): one shared *headless* browser, cheap.
- Paste-any-URL and connected accounts: a dedicated *headful* browser using the
  system **Google Chrome** install (channel="chrome") so the user can watch the
  whole flow and take over.

Live pages are held on the `ApplyRun` in `crawl_store` so `prepare` and a later
`submit`/`refill` — separate HTTP requests — operate on the same page. Abandoned
runs are swept on a TTL."""

from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timedelta, timezone

from app.services.jobs.crawl_store import crawl_store
from app.services.jobs.storage import JOBS_DIR

RUN_TTL = timedelta(minutes=30)

# Dedicated Chrome profile for the visible paste-URL flow (isolated from the
# user's own Chrome profile, but a real Chrome window they can take over).
OWNED_PROFILE_DIR = JOBS_DIR / "chrome-profile"

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_VIEWPORT = {"width": 1366, "height": 1600}

_playwright = None
_browser = None
_lock = asyncio.Lock()


async def _launch(pw, *, headless: bool):
    """Prefer the user's installed Google Chrome; fall back to bundled Chromium."""
    common = {"headless": headless, "args": ["--disable-blink-features=AutomationControlled"]}
    try:
        return await pw.chromium.launch(channel="chrome", **common)
    except Exception:  # noqa: BLE001 - Chrome not installed / channel unavailable
        return await pw.chromium.launch(**common)


async def get_browser():
    """Shared headless browser for ATS-board applies."""
    global _playwright, _browser
    async with _lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        from playwright.async_api import async_playwright

        _playwright = await async_playwright().start()
        _browser = await _launch(_playwright, headless=True)
        return _browser


async def new_context():
    browser = await get_browser()
    return await browser.new_context(viewport=_VIEWPORT, user_agent=_UA)


_owned_lock = asyncio.Lock()


async def new_owned_context(*, headless: bool):
    """A visible **real Google Chrome** window (persistent profile) that owns its
    own Playwright. Used for headful paste-URL / multi-step flows so the user can
    watch and take over. Only one at a time — the caller closes the previous."""
    from playwright.async_api import async_playwright

    async with _owned_lock:
        # A stale ProcessSingleton lock blocks a fresh launch on the same dir.
        for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            try:
                (OWNED_PROFILE_DIR / lock_name).unlink()
            except (FileNotFoundError, OSError):
                pass
        OWNED_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

        pw = await async_playwright().start()
        common = dict(
            user_data_dir=str(OWNED_PROFILE_DIR),
            headless=headless,
            viewport=_VIEWPORT,
            args=["--disable-blink-features=AutomationControlled", "--no-first-run", "--no-default-browser-check"],
        )
        try:
            context = await pw.chromium.launch_persistent_context(channel="chrome", **common)
        except Exception:  # noqa: BLE001 - Chrome channel unavailable
            context = await pw.chromium.launch_persistent_context(**common)
        context._owned_pw = pw  # type: ignore[attr-defined]
        context._owned_browser = None  # type: ignore[attr-defined] - persistent: close context directly
        return context


async def close_owned_context(context) -> None:
    pw = getattr(context, "_owned_pw", None)
    browser = getattr(context, "_owned_browser", None)
    try:
        if browser is not None:
            await browser.close()
        else:
            await context.close()
    except Exception:  # noqa: BLE001
        pass
    finally:
        if pw is not None:
            try:
                await pw.stop()
            except Exception:  # noqa: BLE001
                pass


def reset_owned_profile() -> None:
    shutil.rmtree(OWNED_PROFILE_DIR, ignore_errors=True)


async def acquire_visible_context():
    """A visible Chrome to drive an apply flow in. Prefers the user's own running
    Chrome over CDP (real logins, real profile); otherwise launches a dedicated
    Google Chrome window. Returns (context, page, mode)."""
    from app.services.jobs.apply import cdp

    if await cdp.is_available():
        context = await cdp.connect_context()
        page = await context.new_page()
        context._cdp_page = page  # type: ignore[attr-defined]
        return context, page, "cdp"

    context = await new_owned_context(headless=False)
    page = context.pages[0] if context.pages else await context.new_page()
    return context, page, "chrome"


async def close_run_browser(run) -> None:
    context = getattr(run, "context", None)
    if context is not None:
        from app.services.jobs.apply import cdp

        if cdp.is_cdp_context(context):
            # Leave the tab open for manual/leave-open runs; just detach.
            await cdp.close(context, close_our_tab=not getattr(run, "manual_only", False))
        elif hasattr(context, "_owned_browser"):
            try:
                await close_owned_context(context)
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
        stale = run.updated_at < cutoff
        # Don't reap a still-open manual_only window just because it's old-ish;
        # only reap it past the hard TTL.
        if run.status in {"submitted", "cancelled", "failed"} or stale:
            await close_run_browser(run)
            if stale and run.status not in {"submitted"}:
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
