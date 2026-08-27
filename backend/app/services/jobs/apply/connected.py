"""Connected-account browser sessions for LinkedIn / Wellfound.

These sites have no usable anonymous API for the apply step and prohibit
automated applying. The compromise: the user logs in once in a *visible*
browser window on their own machine; we persist that session's cookies and
reuse them to open (and pre-fill page 1 of) the application, then hand the
window back to the user to finish. Nothing is auto-submitted.

Headful Chromium needs a local display — these features do not work inside the
Docker image.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.services.jobs.storage import JOBS_DIR

SESSIONS_DIR = JOBS_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

LOGIN_URLS: dict[str, str] = {
    "linkedin": "https://www.linkedin.com/login",
    "wellfound": "https://wellfound.com/login",
}

# provider -> (playwright, browser, context) while a connect flow is open
_pending: dict[str, tuple] = {}
_lock = asyncio.Lock()


async def _launch_chrome(pw, *, headless: bool):
    """Use the system Google Chrome install so the user sees a familiar window
    with their extensions/profile chrome; fall back to bundled Chromium."""
    try:
        return await pw.chromium.launch(channel="chrome", headless=headless)
    except Exception:  # noqa: BLE001
        return await pw.chromium.launch(headless=headless)


def session_path(provider: str):
    return SESSIONS_DIR / f"{provider}.json"


def is_connected(provider: str) -> bool:
    return session_path(provider).exists()


def connected_since(provider: str) -> datetime | None:
    path = session_path(provider)
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def disconnect(provider: str) -> bool:
    path = session_path(provider)
    if path.exists():
        path.unlink()
        return True
    return False


async def start_connect(provider: str) -> None:
    async with _lock:
        await _discard_pending(provider)
        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        browser = await _launch_chrome(pw, headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(LOGIN_URLS[provider], wait_until="domcontentloaded")
        _pending[provider] = (pw, browser, context)


async def finish_connect(provider: str) -> None:
    async with _lock:
        entry = _pending.pop(provider, None)
        if entry is None:
            raise ValueError("No connect flow in progress — click Connect first")
        pw, browser, context = entry
        try:
            await context.storage_state(path=str(session_path(provider)))
        finally:
            await browser.close()
            await pw.stop()


async def _discard_pending(provider: str) -> None:
    entry = _pending.pop(provider, None)
    if entry is None:
        return
    pw, browser, _ = entry
    try:
        await browser.close()
    finally:
        await pw.stop()


class NeedsReconnect(RuntimeError):
    pass


async def connected_context(provider: str, headless: bool = False):
    """A fresh browser context carrying the saved login. Caller owns teardown."""
    if not is_connected(provider):
        raise NeedsReconnect(f"Connect your {provider.title()} account first")

    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    browser = await _launch_chrome(pw, headless=headless)
    context = await browser.new_context(storage_state=str(session_path(provider)))
    # Attach the playwright handle so the caller can stop it after closing.
    context.on("close", lambda: None)
    context._owned_pw = pw  # type: ignore[attr-defined]
    context._owned_browser = browser  # type: ignore[attr-defined]
    return context


async def close_connected_context(context) -> None:
    pw = getattr(context, "_owned_pw", None)
    browser = getattr(context, "_owned_browser", None)
    try:
        if browser is not None:
            await browser.close()
    finally:
        if pw is not None:
            await pw.stop()


async def shutdown() -> None:
    for provider in list(_pending):
        await _discard_pending(provider)
