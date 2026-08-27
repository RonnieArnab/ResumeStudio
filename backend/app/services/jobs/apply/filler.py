"""Open an application form, fill it, screenshot it, and stop.

Nothing here submits unless `submit()` is called — which only happens on an
explicit user action in the dashboard, one job at a time."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.jobs.apply.browser import close_run_browser, new_context, sweep_stale_runs
from app.services.jobs.apply.connected import NeedsReconnect, close_connected_context, connected_context
from app.services.jobs.apply.field_extractor import extract_fields
from app.services.jobs.apply.field_mapper import map_fields
from app.services.jobs.crawl_store import crawl_store
from app.services.jobs.models import CONNECTED_PROVIDERS, ApplicantProfile, ApplyRun, FormField, JobPosting
from app.services.jobs.storage import screenshot_path

_CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    ".g-recaptcha",
    "[data-hcaptcha-widget-id]",
    ".cf-turnstile",
    "iframe[title*='challenge']",
]

_COOKIE_BUTTON_TEXTS = ["Accept all", "Accept cookies", "I agree", "Got it", "Allow all"]

_SUBMIT_TEXTS = ["submit application", "submit", "send application", "apply", "send"]


async def _dismiss_cookie_banner(page) -> None:
    for text in _COOKIE_BUTTON_TEXTS:
        try:
            button = page.get_by_role("button", name=text, exact=False)
            if await button.count() > 0:
                await button.first.click(timeout=2000)
                return
        except Exception:  # noqa: BLE001
            continue


async def _detect_captcha(page) -> bool:
    for selector in _CAPTCHA_SELECTORS:
        try:
            if await page.locator(selector).count() > 0:
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def _screenshot(page, run_id: str) -> None:
    try:
        await page.screenshot(path=str(screenshot_path(run_id)), full_page=True)
    except Exception:  # noqa: BLE001 - a viewport shot is better than none
        try:
            await page.screenshot(path=str(screenshot_path(run_id)))
        except Exception:  # noqa: BLE001
            pass


async def _fill_field(page, field: FormField, profile: ApplicantProfile, notes: list[str]) -> None:
    try:
        if field.kind == "file":
            if profile.resume_pdf_path and Path(profile.resume_pdf_path).exists():
                await page.set_input_files(field.selector, profile.resume_pdf_path)
                field.value = Path(profile.resume_pdf_path).name
                field.source = "profile"
            else:
                field.source = "empty"
                notes.append(f"No resume PDF on file — '{field.label}' left empty.")
            return

        if not field.value:
            return

        if field.kind == "select":
            await page.select_option(field.selector, label=field.value)
        elif field.kind == "checkbox":
            if field.value.strip().lower() in {"true", "yes", "1", "on"}:
                await page.check(field.selector, timeout=4000)
        elif field.kind == "radio":
            option_selector = field.option_selectors.get(field.value)
            if option_selector:
                await page.check(option_selector, timeout=4000)
        else:
            await page.fill(field.selector, field.value, timeout=4000)
    except Exception as exc:  # noqa: BLE001 - record and move on
        field.source = "empty"
        notes.append(f"Could not fill '{field.label}': {type(exc).__name__}")


async def _fill_and_capture(page, job: JobPosting, profile: ApplicantProfile, resume_text: str, run: ApplyRun) -> None:
    fields = await extract_fields(page)
    if not fields:
        await page.wait_for_timeout(2500)
        fields = await extract_fields(page)
    if not fields:
        run.notes.append("No form fields detected on the page — the application may open elsewhere.")
    fields = await map_fields(fields, job, profile, resume_text)
    for field in fields:
        await _fill_field(page, field, profile, run.notes)
    run.fields = fields
    run.captcha_detected = await _detect_captcha(page)
    if run.captcha_detected:
        run.notes.append("A CAPTCHA / bot check is present — this application must be submitted manually.")
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:  # noqa: BLE001
        pass
    await page.wait_for_timeout(800)
    await _screenshot(page, run.run_id)


async def prepare(job: JobPosting, profile: ApplicantProfile, resume_text: str) -> ApplyRun:
    await sweep_stale_runs()
    run = ApplyRun(run_id=str(uuid.uuid4()), job=job, profile=profile, status="filling")
    crawl_store.put_run(run)

    if job.provider in CONNECTED_PROVIDERS:
        return await _prepare_connected(job, profile, resume_text, run)

    try:
        context = await new_context()
        page = await context.new_page()
        run.context = context
        run.page = page

        target = job.apply_url or job.url
        await page.goto(target, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_selector("form input, form textarea, input[type=file]", timeout=15000)
        except Exception:  # noqa: BLE001 - fall through and try extraction anyway
            pass
        await page.wait_for_timeout(1500)
        await _dismiss_cookie_banner(page)

        await _fill_and_capture(page, job, profile, resume_text, run)
        run.status = "ready_for_review"
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.notes.append(f"Failed to prepare the form: {exc}")
        await close_run_browser(run)

    run.updated_at = datetime.now(timezone.utc)
    return run


async def _prepare_connected(job: JobPosting, profile: ApplicantProfile, resume_text: str, run: ApplyRun) -> ApplyRun:
    """LinkedIn / Wellfound: open the application in the user's *visible*
    connected browser, fill what's on the first page, and stop. The window is
    left open for the user to finish; this never submits."""
    run.manual_only = True
    try:
        context = await connected_context(job.provider, headless=False)
        page = await context.new_page()
        run.context = context
        run.page = page

        await page.goto(job.url or job.apply_url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2500)

        if "/login" in page.url or "/authwall" in page.url:
            raise NeedsReconnect(f"Your {job.provider.title()} session expired — reconnect it")

        if job.provider == "linkedin":
            clicked = False
            for name in ("Easy Apply", "Apply"):
                try:
                    btn = page.get_by_role("button", name=name, exact=False)
                    if await btn.count() > 0:
                        await btn.first.click(timeout=5000)
                        clicked = True
                        break
                except Exception:  # noqa: BLE001
                    continue
            await page.wait_for_timeout(2000)
            if not clicked:
                run.notes.append("Couldn't find an Easy Apply button — this role may use an external application.")
            run.notes.append("Easy Apply is multi-step: page 1 is filled below, finish the rest in the open browser window.")

        await _fill_and_capture(page, job, profile, resume_text, run)
        run.notes.append("The browser window is open — review and submit there yourself.")
        run.status = "ready_for_review"
    except NeedsReconnect as exc:
        run.status = "failed"
        run.notes.append(str(exc))
        await _teardown_connected(run)
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.notes.append(f"Failed to open the application: {exc}")
        await _teardown_connected(run)

    run.updated_at = datetime.now(timezone.utc)
    return run


async def _teardown_connected(run: ApplyRun) -> None:
    if run.context is not None:
        await close_connected_context(run.context)
    run.page = None
    run.context = None


async def refill(run: ApplyRun, overrides: dict[str, str]) -> ApplyRun:
    if run.page is None:
        run.notes.append("This run's browser session has expired — start a new preparation.")
        run.status = "failed"
        return run

    by_selector = {f.selector: f for f in run.fields}
    for selector, value in overrides.items():
        field = by_selector.get(selector)
        if field is None:
            continue
        field.value = value
        field.source = "user"
        await _fill_field(run.page, field, run.profile, run.notes)

    await run.page.wait_for_timeout(300)
    await _screenshot(run.page, run.run_id)
    run.status = "ready_for_review"
    run.updated_at = datetime.now(timezone.utc)
    return run


async def _find_submit(page):
    for text in _SUBMIT_TEXTS:
        for role in ("button", "link"):
            try:
                locator = page.get_by_role(role, name=text, exact=False)
                if await locator.count() > 0:
                    return locator.last
            except Exception:  # noqa: BLE001
                continue
    try:
        fallback = page.locator("button[type=submit], input[type=submit]")
        if await fallback.count() > 0:
            return fallback.last
    except Exception:  # noqa: BLE001
        pass
    return None


async def submit(run: ApplyRun) -> ApplyRun:
    if run.manual_only:
        run.notes.append("This application must be finished by you in the open browser window — it won't be submitted from here.")
        return run
    if run.captcha_detected:
        run.notes.append("Refusing to submit: a CAPTCHA is present. Finish this one in the browser yourself.")
        return run
    if run.page is None:
        run.status = "failed"
        run.notes.append("Browser session expired before submit.")
        return run

    run.status = "submitting"
    page = run.page
    try:
        button = await _find_submit(page)
        if button is None:
            run.status = "ready_for_review"
            run.notes.append("Could not locate a submit button — submit manually in the browser.")
            return run

        await button.click(timeout=8000)
        try:
            await page.wait_for_load_state("networkidle", timeout=25000)
        except Exception:  # noqa: BLE001 - SPA confirmations don't always settle
            await page.wait_for_timeout(3000)

        body_text = (await page.inner_text("body"))[:4000]
        run.confirmation_text = _extract_confirmation(body_text)
        await _screenshot(page, run.run_id)
        run.status = "submitted"
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.notes.append(f"Submit failed: {exc}")
    finally:
        await close_run_browser(run)
        run.updated_at = datetime.now(timezone.utc)

    return run


def _extract_confirmation(body_text: str) -> str:
    lowered = body_text.lower()
    for marker in ("thank you for applying", "application received", "successfully submitted", "thanks for applying", "we received your application"):
        idx = lowered.find(marker)
        if idx != -1:
            return body_text[idx : idx + 200].strip()
    return body_text[:200].strip()
