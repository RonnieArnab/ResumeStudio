"""Attach Playwright to a Google Chrome the user launched themselves with remote
debugging enabled, over the Chrome DevTools Protocol.

This runs the apply flow in the user's **real, already-logged-in Chrome
profile** — their LinkedIn / Wellfound / Google SSO sessions are just there, and
they watch it happen in a normal tab and can take over at any point.

Setup (all normal Chrome windows must be closed first):

    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\
        --remote-debugging-port=9222 \\
        --user-data-dir="$HOME/.chrome-remote-profile"

Then apply from a URL / to a LinkedIn job as usual.
"""

from __future__ import annotations

import os

import httpx

CDP_PORT = int(os.environ.get("CHROME_CDP_PORT", "9222"))
CDP_HTTP = f"http://127.0.0.1:{CDP_PORT}"

_CHROME_MAC = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class CdpUnavailable(RuntimeError):
    pass


def launch_command() -> str:
    """The one-liner the user runs to expose their Chrome to us (macOS)."""
    return (
        f'"{_CHROME_MAC}" --remote-debugging-port={CDP_PORT} '
        f'--user-data-dir="$HOME/.chrome-remote-profile" --no-first-run'
    )


async def is_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{CDP_HTTP}/json/version")
            return resp.status_code == 200
    except (httpx.HTTPError, OSError):
        return False


async def describe() -> dict:
    info: dict = {"available": False, "port": CDP_PORT, "launch_command": launch_command()}
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{CDP_HTTP}/json/version")
            if resp.status_code == 200:
                data = resp.json()
                info["available"] = True
                info["browser"] = data.get("Browser", "")
    except (httpx.HTTPError, OSError):
        pass
    return info


async def connect_context():
    """A context bound to the user's running Chrome. Reuses their existing
    default context (real cookies/logins). Caller tears down with `close`."""
    if not await is_available():
        raise CdpUnavailable(
            f"No Chrome with remote debugging on port {CDP_PORT}. Launch it with:\n{launch_command()}"
        )

    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.connect_over_cdp(CDP_HTTP)
    except Exception as exc:  # noqa: BLE001
        await pw.stop()
        raise CdpUnavailable(f"Could not attach to Chrome on {CDP_HTTP}: {exc}") from exc

    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    context._cdp_pw = pw  # type: ignore[attr-defined]
    context._cdp_browser = browser  # type: ignore[attr-defined]
    return context


def is_cdp_context(context) -> bool:
    return hasattr(context, "_cdp_browser")


_LOGIN_URLS = {
    "linkedin": "https://www.linkedin.com/login",
    "wellfound": "https://wellfound.com/login",
    "google": "https://accounts.google.com/",
}


async def open_login_tab(provider: str) -> dict:
    """Open the provider's sign-in page as a NEW TAB in the user's running
    Chrome. Because it's their real browser, an existing Google session makes
    the LinkedIn/Wellfound "Continue with Google" flow one click — and the tab
    is left in front for them to finish."""
    url = _LOGIN_URLS.get(provider)
    if not url:
        raise CdpUnavailable(f"No login URL for '{provider}'")

    context = await connect_context()
    try:
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            await page.bring_to_front()
        except Exception:  # noqa: BLE001
            pass
        return {"opened": url}
    finally:
        # detach but keep the tab open
        pw = getattr(context, "_cdp_pw", None)
        if pw is not None:
            try:
                await pw.stop()
            except Exception:  # noqa: BLE001
                pass


async def close(context, *, close_our_tab: bool) -> None:
    """Detach from the user's Chrome. Never closes their browser. Closes only the
    single tab we opened, and only when the run isn't a leave-open manual one."""
    pw = getattr(context, "_cdp_pw", None)
    our_page = getattr(context, "_cdp_page", None)
    if close_our_tab and our_page is not None:
        try:
            await our_page.close()
        except Exception:  # noqa: BLE001
            pass
    if pw is not None:
        try:
            await pw.stop()  # disconnects; the user's Chrome keeps running
        except Exception:  # noqa: BLE001
            pass
