"""Open an application form, fill it, screenshot it, and stop.

Nothing here submits unless `submit()` is called — which only happens on an
explicit user action in the dashboard, one job at a time.

Three shapes of apply flow:
  - ATS boards (Greenhouse/Lever/Ashby): single embedded form, headless.
  - LinkedIn / Wellfound: connected browser, fill Easy-Apply page 1, stop.
  - Paste-any-URL ("other"): headful Google Chrome, click through "Apply",
    handle an email pre-step, walk the multi-step wizard filling each page,
    screenshot every step, stop before the final Submit.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.jobs.apply.browser import (
    acquire_visible_context,
    close_run_browser,
    new_context,
    sweep_stale_runs,
)
from app.services.jobs.apply import cdp
from app.services.jobs.apply.connected import NeedsReconnect, connected_context, is_connected
from app.services.jobs.apply.field_extractor import extract_fields
from app.services.jobs.apply.field_mapper import map_fields
from app.services.jobs.crawl_store import crawl_store
from app.services.jobs.models import CONNECTED_PROVIDERS, ApplicantProfile, ApplyRun, FormField, JobPosting
from app.services.jobs.storage import screenshot_path
from app.services.jobs.tracker import record_apply

_CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    ".g-recaptcha",
    "[data-hcaptcha-widget-id]",
    ".cf-turnstile",
    "iframe[title*='challenge']",
]

_COOKIE_TEXTS = [
    "Accept all", "Accept All", "Accept cookies", "Accept Cookies", "Accept", "ACCEPT",
    "I agree", "I Agree", "Agree", "Got it", "Allow all", "OK", "Continue",
]

_APPLY_TEXTS = ["apply now", "apply for this job", "apply to this job", "start your application", "apply"]
_APPLY_EXCLUDE = ("linkedin", "indeed", "google", "with ", "seek", "view", "more jobs", "share", "save")

_NEXT_TEXTS = ["save and continue", "save & continue", "continue", "next", "next step", "review"]

_SUBMIT_TEXTS = ["submit application", "submit", "send application", "send"]

_CONSENT_WORDS = (
    "agree", "consent", "terms", "conditions", "acknowledge", "certify", "privacy",
    "gdpr", "i have read", "truthful", "accurate and complete",
)


# --------------------------------------------------------------------------- #
# Low-level helpers                                                            #
# --------------------------------------------------------------------------- #


async def _dismiss_cookie_banner(page) -> None:
    for text in _COOKIE_TEXTS:
        for exact in (True, False):
            try:
                btn = page.get_by_role("button", name=text, exact=exact)
                if await btn.count() > 0 and await btn.first.is_visible():
                    await btn.first.click(timeout=2000)
                    await page.wait_for_timeout(400)
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


async def _screenshot(page, run: ApplyRun, title: str, note: str = "") -> None:
    step = len(run.step_meta)
    for full in (True, False):
        try:
            await page.screenshot(path=str(screenshot_path(run.run_id, step)), full_page=full)
            break
        except Exception:  # noqa: BLE001
            continue
    run.step_meta.append((step, title, note))


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
        elif field.kind == "combobox":
            loc = page.locator(field.selector)
            await loc.click(timeout=3000)
            await loc.fill(field.value, timeout=3000)
            await page.wait_for_timeout(700)
            # pick the first matching option from the popup listbox
            option = page.locator("[role=option], li[role=option], .oj-listbox-result").filter(has_text=field.value)
            try:
                if await option.count() > 0:
                    await option.first.click(timeout=2000)
                else:
                    await page.keyboard.press("ArrowDown")
                    await page.keyboard.press("Enter")
            except Exception:  # noqa: BLE001
                await page.keyboard.press("Enter")
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


async def _check_consent_boxes(page) -> int:
    """Tick unchecked terms/consent/certification checkboxes — you can't apply
    without agreeing, and the model won't reliably answer these."""
    ticked = 0
    try:
        boxes = await page.locator("input[type=checkbox]:visible").all()
    except Exception:  # noqa: BLE001
        return 0
    for cb in boxes:
        try:
            if await cb.is_checked():
                continue
            label = ""
            for getter in ("aria-label",):
                label = (await cb.get_attribute(getter)) or ""
            if not label:
                handle = await cb.element_handle()
                if handle:
                    label = await page.evaluate(
                        "(el) => (el.labels && el.labels[0] && el.labels[0].innerText) || "
                        "(el.closest('label') && el.closest('label').innerText) || "
                        "(el.parentElement && el.parentElement.innerText) || ''",
                        handle,
                    )
            if any(w in label.lower() for w in _CONSENT_WORDS):
                await cb.check(timeout=2500)
                ticked += 1
        except Exception:  # noqa: BLE001
            continue
    return ticked


async def _fill_current_form(page, job: JobPosting, profile: ApplicantProfile, resume_text: str, run: ApplyRun) -> list[FormField]:
    fields = await extract_fields(page)
    if not fields:
        await page.wait_for_timeout(3000)
        fields = await extract_fields(page)
    fields = await map_fields(fields, job, profile, resume_text)
    for field in fields:
        await _fill_field(page, field, profile, run.notes)
    await _check_consent_boxes(page)
    try:
        await page.wait_for_load_state("networkidle", timeout=6000)
    except Exception:  # noqa: BLE001
        pass
    await page.wait_for_timeout(700)
    return fields


async def _find_by_texts(page, texts: list[str], roles=("button", "link"), exclude: tuple[str, ...] = ()):
    # exact matches first (so "Apply" beats "Apply with LinkedIn"), then loose.
    for exact in (True, False):
        for text in texts:
            for role in roles:
                try:
                    loc = page.get_by_role(role, name=text, exact=exact)
                    n = min(await loc.count(), 8)
                    for i in range(n):
                        cand = loc.nth(i)
                        if not (await cand.is_visible() and await cand.is_enabled()):
                            continue
                        name = ((await cand.get_attribute("aria-label")) or (await cand.inner_text()) or "").lower()
                        if any(x in name for x in exclude):
                            continue
                        return cand
                except Exception:  # noqa: BLE001
                    continue
    return None


# --------------------------------------------------------------------------- #
# prepare()                                                                    #
# --------------------------------------------------------------------------- #


async def _close_open_manual_runs() -> None:
    """Only one visible apply window/tab at a time — close any prior manual run
    (its tab too, even for CDP, so the user's Chrome doesn't pile up tabs)."""
    for other in crawl_store.all_runs():
        if other.manual_only and other.context is not None:
            page = getattr(other, "page", None)
            if page is not None:
                try:
                    await page.close()
                except Exception:  # noqa: BLE001
                    pass
            other.manual_only = False  # let close_run_browser fully detach
            await close_run_browser(other)
            other.status = "cancelled"
            crawl_store.drop_run(other.run_id)


async def prepare(job: JobPosting, profile: ApplicantProfile, resume_text: str) -> ApplyRun:
    await sweep_stale_runs()
    run = ApplyRun(run_id=str(uuid.uuid4()), job=job, profile=profile, status="filling")
    crawl_store.put_run(run)

    if job.provider in CONNECTED_PROVIDERS:
        result = await _prepare_connected(job, profile, resume_text, run)
    elif job.provider == "other":
        result = await _prepare_multistep(job, profile, resume_text, run)
    else:
        result = await _prepare_ats(job, profile, resume_text, run)

    if result.status == "ready_for_review":
        try:
            record_apply(job, status="preparing", source="apply")
        except Exception:  # noqa: BLE001 - tracker must never break an apply
            pass
    return result


async def _prepare_ats(job: JobPosting, profile: ApplicantProfile, resume_text: str, run: ApplyRun) -> ApplyRun:
    try:
        context = await new_context()
        page = await context.new_page()
        run.context = context
        run.page = page

        await page.goto(job.apply_url or job.url, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_selector("form input, form textarea, input[type=file]", timeout=15000)
        except Exception:  # noqa: BLE001
            pass
        await page.wait_for_timeout(1500)
        await _dismiss_cookie_banner(page)

        fields = await _fill_current_form(page, job, profile, resume_text, run)
        if not fields:
            run.notes.append("No form fields detected — the application may open elsewhere.")
        run.fields = fields
        run.captcha_detected = await _detect_captcha(page)
        if run.captcha_detected:
            run.notes.append("A CAPTCHA / bot check is present — submit this one manually.")
        await _screenshot(page, run, "Application form")
        run.status = "ready_for_review"
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.notes.append(f"Failed to prepare the form: {exc}")
        await close_run_browser(run)

    run.updated_at = datetime.now(timezone.utc)
    return run


async def _prepare_multistep(job: JobPosting, profile: ApplicantProfile, resume_text: str, run: ApplyRun) -> ApplyRun:
    """Paste-any-URL: a visible Google Chrome window walks the whole apply flow."""
    run.manual_only = True
    MAX_STEPS = 7
    await _close_open_manual_runs()
    try:
        context, page, mode = await acquire_visible_context()
        run.context = context
        run.page = page
        if mode == "cdp":
            run.notes.append("Running in your open Chrome (attached over the DevTools protocol).")

        await page.goto(job.url or job.apply_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2500)
        await _dismiss_cookie_banner(page)
        await _identify_job(page, job)
        await _screenshot(page, run, "Job posting", "Opened the link")

        # 1. Job preview pages just link to the form — click "Apply".
        apply_btn = await _find_by_texts(page, _APPLY_TEXTS, exclude=_APPLY_EXCLUDE)
        if apply_btn is not None:
            await apply_btn.click(timeout=8000)
            await _settle(page, 5000)
            await _dismiss_cookie_banner(page)
            run.notes.append("Clicked the Apply button.")

        # 2. Oracle-style email pre-step: email + agree checkbox + Next.
        await _handle_email_prestep(page, profile, run)

        # 3. Walk the wizard.
        last_fingerprint = ""
        stalls = 0
        for step_num in range(1, MAX_STEPS + 1):
            await _settle(page, 1500)
            fields = await _fill_current_form(page, job, profile, resume_text, run)
            run.fields = fields  # keep the latest step's fields for the review table
            run.captcha_detected = run.captcha_detected or await _detect_captcha(page)

            heading = await _page_heading(page)
            step_captcha = await _detect_captcha(page)
            run.captcha_detected = run.captcha_detected or step_captcha
            note = f"{len(fields)} field(s) filled" + (" · CAPTCHA blocking this step" if step_captcha else "")
            await _screenshot(page, run, heading or f"Step {step_num}", note)

            if step_captcha:
                run.notes.append(
                    "A CAPTCHA is blocking this step — solve it in the open Chrome window, then continue the application there."
                )
                break

            submit_btn = await _find_by_texts(page, _SUBMIT_TEXTS)
            next_btn = await _find_by_texts(page, _NEXT_TEXTS)
            if submit_btn is not None and next_btn is None:
                run.notes.append(f"Reached the review / submit step ({heading or 'final step'}) — stopping for you to submit.")
                break
            if next_btn is None:
                run.notes.append("No further step button found — finish the application in the open window.")
                break

            fp = f"{page.url}::{heading}::{len(fields)}::{'|'.join(f.label for f in fields[:3])}"
            if fp == last_fingerprint:
                stalls += 1
                if stalls >= 2:
                    run.notes.append("The form stopped advancing (a required field it couldn't fill) — continue in the window.")
                    break
            else:
                stalls = 0
            last_fingerprint = fp

            try:
                await next_btn.scroll_into_view_if_needed(timeout=2000)
                await next_btn.click(timeout=8000)
            except Exception:  # noqa: BLE001
                run.notes.append("Couldn't click the next-step button — continue in the window.")
                break
            await _settle(page, 2000)
        else:
            run.notes.append(f"Stopped after {MAX_STEPS} steps — continue in the open window.")

        if run.captcha_detected:
            run.notes.append("A CAPTCHA appeared during the flow.")
        run.notes.append("The Chrome window is open — review each step above, then submit there yourself.")
        run.status = "ready_for_review"
    except Exception as exc:  # noqa: BLE001
        # If we already walked a step or two, that's still a useful result —
        # don't blow the whole run away just because the page later died.
        if len(run.step_meta) >= 2:
            run.notes.append(f"Stopped early ({type(exc).__name__}) — continue in the open window.")
            run.status = "ready_for_review"
        else:
            run.status = "failed"
            run.notes.append(f"Multi-step apply failed: {exc}")
            await _teardown(run)

    run.updated_at = datetime.now(timezone.utc)
    return run


async def _handle_email_prestep(page, profile: ApplicantProfile, run: ApplyRun) -> None:
    try:
        try:
            await page.wait_for_selector("input[type=email], input[name*=email i]", timeout=8000)
        except Exception:  # noqa: BLE001
            return
        email_input = page.locator("input[type=email], input[name*=email i], input[id*=email i]").first
        if await email_input.count() == 0 or not await email_input.is_visible():
            return
        # only treat as a pre-step if the page is sparse (just email + agree + honeypot)
        all_inputs = await page.locator("input:visible, textarea:visible, select:visible").count()
        if all_inputs > 5:
            return
        if profile.email:
            await email_input.fill(profile.email, timeout=4000)
        await _check_consent_boxes(page)
        for cb in await page.locator("input[type=checkbox]:visible").all():
            try:
                if not await cb.is_checked():
                    await cb.check(timeout=1500)
            except Exception:  # noqa: BLE001
                pass
        await _screenshot(page, run, "Enter email address", "Filled email + accepted terms")
        nxt = await _find_by_texts(page, ["next", "continue", "get started"])
        if nxt is not None:
            await nxt.click(timeout=6000)
            await _settle(page, 4000)
            run.notes.append("Passed the email / terms pre-step.")
    except Exception:  # noqa: BLE001
        pass


async def _identify_job(page, job: JobPosting) -> None:
    """Pull the real role title / company off the posting page so the tracker
    and review header show something meaningful for a pasted URL."""
    if job.title and job.title != "Pasted job URL":
        return
    try:
        heading = await _page_heading(page)
        page_title = (await page.title()) or ""
        og_site = await page.locator("meta[property='og:site_name']").first.get_attribute("content")
    except Exception:  # noqa: BLE001
        return
    title = heading or page_title.split("|")[0].split(" - ")[0].strip()
    if title and 3 < len(title) < 120:
        job.title = title
    if og_site:
        job.company = og_site.strip()


async def _settle(page, extra_ms: int) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:  # noqa: BLE001
        pass
    await page.wait_for_timeout(extra_ms)


async def _page_heading(page) -> str:
    for sel in ("h1", "h2", "[role=heading]"):
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                txt = (await loc.inner_text()).strip()
                if txt:
                    return txt[:80]
        except Exception:  # noqa: BLE001
            continue
    return ""


async def _prepare_connected(job: JobPosting, profile: ApplicantProfile, resume_text: str, run: ApplyRun) -> ApplyRun:
    """LinkedIn / Wellfound: open in the user's real Chrome (preferred, via CDP)
    or a stored connected session, fill Easy-Apply page 1, and stop."""
    run.manual_only = True
    await _close_open_manual_runs()
    provider_name = job.provider.title()
    try:
        if await cdp.is_available():
            context, page, _ = await acquire_visible_context()
            run.notes.append(f"Using your open Chrome — your {provider_name} login is used directly.")
        elif is_connected(job.provider):
            context = await connected_context(job.provider, headless=False)
            page = await context.new_page()
        else:
            raise NeedsReconnect(
                f"Connect your {provider_name} account, or open Chrome with remote debugging, then try again."
            )
        run.context = context
        run.page = page

        await page.goto(job.url or job.apply_url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2500)
        if "/login" in page.url or "/authwall" in page.url or "/signup" in page.url:
            run.notes.append(
                f"Not signed in to {provider_name} in this browser. Sign in in the tab that's now open "
                f"(use “Continue with Google” if you're logged into Google), then re-run apply."
            )
            try:
                await page.goto(f"https://www.{job.provider}.com/login", wait_until="domcontentloaded", timeout=20000)
                await page.bring_to_front()
            except Exception:  # noqa: BLE001
                pass
            await _screenshot(page, run, f"{provider_name} sign-in required")
            run.status = "ready_for_review"
            run.updated_at = datetime.now(timezone.utc)
            return run

        if job.provider == "linkedin":
            btn = await _find_by_texts(page, ["easy apply", "apply"], roles=("button",))
            if btn is not None:
                await btn.click(timeout=5000)
                await page.wait_for_timeout(2000)
            else:
                run.notes.append("No Easy Apply button — this role may use an external application.")
            run.notes.append("Easy Apply is multi-step: page 1 is filled, finish the rest in the open window.")

        fields = await _fill_current_form(page, job, profile, resume_text, run)
        run.fields = fields
        run.captcha_detected = await _detect_captcha(page)
        await _screenshot(page, run, "Easy Apply — page 1")
        run.notes.append("The browser window is open — review and submit there yourself.")
        run.status = "ready_for_review"
    except NeedsReconnect as exc:
        run.status = "failed"
        run.notes.append(str(exc))
        await _teardown(run)
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.notes.append(f"Failed to open the application: {exc}")
        await _teardown(run)

    run.updated_at = datetime.now(timezone.utc)
    return run


async def _teardown(run: ApplyRun) -> None:
    await close_run_browser(run)


# --------------------------------------------------------------------------- #
# refill() / submit()                                                          #
# --------------------------------------------------------------------------- #


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
    await _screenshot(run.page, run, "After your edits")
    run.status = "ready_for_review"
    run.updated_at = datetime.now(timezone.utc)
    return run


async def submit(run: ApplyRun) -> ApplyRun:
    if run.manual_only:
        run.notes.append("Finish this one in the open browser window — it won't be submitted from here.")
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
        button = await _find_by_texts(page, _SUBMIT_TEXTS) or page.locator("button[type=submit], input[type=submit]").last
        if button is None or await button.count() == 0:
            run.status = "ready_for_review"
            run.notes.append("Could not locate a submit button — submit manually in the browser.")
            return run

        await button.click(timeout=8000)
        try:
            await page.wait_for_load_state("networkidle", timeout=25000)
        except Exception:  # noqa: BLE001
            await page.wait_for_timeout(3000)

        body_text = (await page.inner_text("body"))[:4000]
        run.confirmation_text = _extract_confirmation(body_text)
        await _screenshot(page, run, "Submitted")
        run.status = "submitted"
        try:
            record_apply(run.job, status="applied", source="submit", notes=run.confirmation_text or "")
        except Exception:  # noqa: BLE001
            pass
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
