"""Job crawler + auto-apply API.

Discovery hits the ATS providers' official public JSON APIs. The apply flow
drives a headless browser to *fill* a form and then stops — submission happens
only via the explicit `/submit` endpoint, one job at a time.
"""

from __future__ import annotations

import hashlib
import shutil

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.services.agent.streaming import format_sse
from app.services.jobs.apply import connected, filler
from app.services.jobs.ats import SEARCH_PROVIDERS, parse_board_ref
from app.services.jobs.ats.registry import search_registry
from app.services.jobs.crawl import run_crawl
from app.services.jobs.crawl_store import crawl_store
from app.services.jobs.models import (
    AddSourceRequest,
    AutofillProfileRequest,
    ApplicantProfile,
    ApplyRunView,
    BoardSource,
    CONNECTED_PROVIDERS,
    ConnectionStatus,
    CrawlRequest,
    FieldOverridesRequest,
    JobPosting,
    PrepareApplyRequest,
    PrepareUrlRequest,
    Provider,
    RankedJob,
    RegistryEntry,
    SetProfileResumeRequest,
)
from app.services.jobs.profile_store import load_profile, save_profile
from app.services.jobs.resume_text import latex_to_plain_text
from app.services.jobs.storage import RESUME_DIR, screenshot_path
from app.services.jobs.tracker import (
    Application,
    ApplicationCreate,
    ApplicationUpdate,
    add_application,
    delete_application,
    list_applications,
    update_application,
)
from app.services.latex.compiler import COMPILED_ROOT
from app.services.session.session_store import session_store

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# --------------------------------------------------------------------------- #
# Board sources                                                                #
# --------------------------------------------------------------------------- #


@router.get("/sources", response_model=list[BoardSource])
async def list_sources() -> list[BoardSource]:
    return crawl_store.list_sources()


@router.post("/sources", response_model=BoardSource)
async def add_source(body: AddSourceRequest) -> BoardSource:
    # Search source: LinkedIn / Wellfound keyword search.
    if body.provider in SEARCH_PROVIDERS and body.query:
        return crawl_store.add_search_source(body.provider, body.query.strip(), (body.location or "").strip(), body.label)

    if not body.ref:
        raise HTTPException(status_code=400, detail="Provide a board URL / provider:slug, or a search provider + query")
    try:
        provider, slug = parse_board_ref(body.ref)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return crawl_store.add_board_source(provider, slug, body.label)


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str) -> dict[str, bool]:
    return {"removed": crawl_store.remove_source(source_id)}


@router.get("/registry", response_model=list[RegistryEntry])
async def company_registry(q: str = "") -> list[RegistryEntry]:
    return search_registry(q)


@router.get("/cdp/status")
async def cdp_status() -> dict:
    from app.services.jobs.apply import cdp

    return await cdp.describe()


# --------------------------------------------------------------------------- #
# Applied-jobs tracker                                                         #
# --------------------------------------------------------------------------- #


@router.get("/applications", response_model=list[Application])
async def get_applications() -> list[Application]:
    return list_applications()


@router.post("/applications", response_model=Application)
async def create_application(body: ApplicationCreate) -> Application:
    return add_application(body)


@router.patch("/applications/{app_id}", response_model=Application)
async def patch_application(app_id: str, body: ApplicationUpdate) -> Application:
    updated = update_application(app_id, body)
    if updated is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return updated


@router.delete("/applications/{app_id}")
async def remove_application(app_id: str) -> dict[str, bool]:
    return {"removed": delete_application(app_id)}


# --------------------------------------------------------------------------- #
# Connected accounts (LinkedIn / Wellfound)                                    #
# --------------------------------------------------------------------------- #


def _check_connected_provider(provider: str) -> None:
    if provider not in CONNECTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"'{provider}' is not a connectable provider")


@router.get("/connect", response_model=list[ConnectionStatus])
async def list_connections() -> list[ConnectionStatus]:
    return [
        ConnectionStatus(provider=p, connected=connected.is_connected(p), since=connected.connected_since(p))
        for p in CONNECTED_PROVIDERS
    ]


@router.post("/connect/{provider}/start")
async def connect_start(provider: str) -> dict[str, str]:
    _check_connected_provider(provider)
    try:
        await connected.start_connect(provider)
    except Exception as exc:  # noqa: BLE001 - headful launch can fail on a headless host
        raise HTTPException(status_code=500, detail=f"Could not open a browser: {exc}") from exc
    return {"status": "waiting_for_login"}


@router.post("/connect/{provider}/finish", response_model=ConnectionStatus)
async def connect_finish(provider: str) -> ConnectionStatus:
    _check_connected_provider(provider)
    try:
        await connected.finish_connect(provider)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ConnectionStatus(provider=provider, connected=True, since=connected.connected_since(provider))


@router.delete("/connect/{provider}")
async def connect_delete(provider: str) -> dict[str, bool]:
    _check_connected_provider(provider)
    return {"removed": connected.disconnect(provider)}


@router.post("/connect/{provider}/open-login")
async def connect_open_login(provider: str) -> dict:
    """Open the provider's sign-in page in a new tab of the user's running
    Chrome (needs the CDP connection)."""
    if provider not in (*CONNECTED_PROVIDERS, "google"):
        raise HTTPException(status_code=400, detail=f"Can't open a login tab for '{provider}'")
    from app.services.jobs.apply import cdp

    try:
        return await cdp.open_login_tab(provider)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# --------------------------------------------------------------------------- #
# Crawl (SSE)                                                                  #
# --------------------------------------------------------------------------- #


def _resume_text_for(body: CrawlRequest) -> str | None:
    if body.resume_session_id:
        session = session_store.get(body.resume_session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Resume session not found")
        return latex_to_plain_text(session.latex)
    if body.resume_text and body.resume_text.strip():
        return body.resume_text.strip()
    return None


@router.post("/crawl")
async def crawl(body: CrawlRequest) -> StreamingResponse:
    resume_text = _resume_text_for(body)

    years = body.target_years_experience
    if years is None:
        prof_years = load_profile().years_experience
        m = "".join(c for c in (prof_years or "") if c.isdigit())
        years = int(m) if m else None

    async def event_stream():
        async for event in run_crawl(
            resume_text,
            posted_within_days=body.posted_within_days,
            target_years_experience=years,
        ):
            yield format_sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# --------------------------------------------------------------------------- #
# Profile                                                                      #
# --------------------------------------------------------------------------- #


@router.get("/profile", response_model=ApplicantProfile)
async def get_profile() -> ApplicantProfile:
    return load_profile()


@router.put("/profile", response_model=ApplicantProfile)
async def put_profile(body: ApplicantProfile) -> ApplicantProfile:
    return save_profile(body)


@router.post("/profile/from-resume", response_model=ApplicantProfile)
async def autofill_profile_from_resume(body: AutofillProfileRequest) -> ApplicantProfile:
    """Pull name / email / phone / links / location / years of experience out of
    the uploaded resume and populate the profile, and attach the compiled PDF."""
    session = session_store.get(body.resume_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Resume session not found")

    from app.services.jobs.profile_extract import apply_extracted, extract_profile_fields

    resume_text = latex_to_plain_text(session.latex)
    fields = await extract_profile_fields(resume_text, raw_latex=session.latex)

    profile = load_profile()
    apply_extracted(profile, fields, overwrite=body.overwrite)

    source_pdf = COMPILED_ROOT / body.resume_session_id / "resume.pdf"
    if source_pdf.exists():
        dest = RESUME_DIR / f"{body.resume_session_id}.pdf"
        shutil.copyfile(source_pdf, dest)
        profile.resume_pdf_path = str(dest)
        profile.resume_source_label = f"resume session {body.resume_session_id[:8]}"

    return save_profile(profile)


@router.post("/profile/resume", response_model=ApplicantProfile)
async def set_profile_resume_from_session(body: SetProfileResumeRequest) -> ApplicantProfile:
    session = session_store.get(body.resume_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Resume session not found")

    source_pdf = COMPILED_ROOT / body.resume_session_id / "resume.pdf"
    if not source_pdf.exists():
        raise HTTPException(status_code=409, detail="That resume session has no compiled PDF yet")

    dest = RESUME_DIR / f"{body.resume_session_id}.pdf"
    shutil.copyfile(source_pdf, dest)

    profile = load_profile()
    profile.resume_pdf_path = str(dest)
    profile.resume_source_label = f"resume session {body.resume_session_id[:8]}"
    return save_profile(profile)


@router.post("/profile/resume/upload", response_model=ApplicantProfile)
async def upload_profile_resume(file: UploadFile = File(...)) -> ApplicantProfile:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF")
    dest = RESUME_DIR / "uploaded.pdf"
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    dest.write_bytes(contents)

    profile = load_profile()
    profile.resume_pdf_path = str(dest)
    profile.resume_source_label = file.filename
    return save_profile(profile)


# --------------------------------------------------------------------------- #
# Job listing                                                                  #
# --------------------------------------------------------------------------- #


@router.get("", response_model=list[RankedJob])
async def list_jobs(
    min_score: int = Query(0, ge=0, le=100),
    location_contains: str | None = None,
    provider: Provider | None = None,
    remote_only: bool = False,
    posted_within_days: int | None = Query(None, ge=1),
) -> list[RankedJob]:
    return crawl_store.ranked_jobs(
        min_score=min_score,
        location_contains=location_contains,
        provider=provider,
        remote_only=remote_only,
        posted_within_days=posted_within_days,
    )


@router.get("/{job_id}", response_model=RankedJob)
async def job_detail(job_id: str) -> RankedJob:
    job = crawl_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return RankedJob(job=job, match=crawl_store.get_match(job_id))


# --------------------------------------------------------------------------- #
# Apply flow                                                                   #
# --------------------------------------------------------------------------- #


def _run_view(run) -> ApplyRunView:
    v = int(run.updated_at.timestamp() * 1000)
    return run.to_view(lambda step: f"/api/jobs/apply/{run.run_id}/screenshot?step={step}&v={v}")


@router.post("/apply/prepare", response_model=ApplyRunView)
async def prepare_application(body: PrepareApplyRequest) -> ApplyRunView:
    job: JobPosting | None = crawl_store.get_job(body.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found — run a crawl first")

    profile = load_profile()
    if not profile.email or not profile.full_name:
        raise HTTPException(status_code=409, detail="Fill in at least your name and email in the profile first")

    resume_text = ""
    if body.resume_session_id:
        session = session_store.get(body.resume_session_id)
        if session is not None:
            resume_text = latex_to_plain_text(session.latex)

    run = await filler.prepare(job, profile, resume_text)
    return _run_view(run)


@router.post("/apply/prepare-url", response_model=ApplyRunView)
async def prepare_application_from_url(body: PrepareUrlRequest) -> ApplyRunView:
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Provide a full http(s) job URL")

    profile = load_profile()
    if not profile.email or not profile.full_name:
        raise HTTPException(status_code=409, detail="Fill in at least your name and email in the profile first")

    job_id = "other:" + hashlib.sha1(url.encode()).hexdigest()[:12]
    job = JobPosting(
        id=job_id,
        provider="other",
        company=body.title or url.split("/")[2],
        title=body.title or "Pasted job URL",
        url=url,
        apply_url=url,
    )
    crawl_store.upsert_job(job)

    resume_text = ""
    if body.resume_session_id:
        session = session_store.get(body.resume_session_id)
        if session is not None:
            resume_text = latex_to_plain_text(session.latex)

    run = await filler.prepare(job, profile, resume_text)
    return _run_view(run)


@router.put("/apply/{run_id}/fields", response_model=ApplyRunView)
async def edit_application_fields(run_id: str, body: FieldOverridesRequest) -> ApplyRunView:
    run = crawl_store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Apply run not found or expired")
    run = await filler.refill(run, body.overrides)
    return _run_view(run)


@router.post("/apply/{run_id}/submit", response_model=ApplyRunView)
async def submit_application(run_id: str) -> ApplyRunView:
    run = crawl_store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Apply run not found or expired")
    if run.status != "ready_for_review":
        raise HTTPException(status_code=409, detail=f"Run is '{run.status}', not ready for submit")
    run = await filler.submit(run)
    return _run_view(run)


@router.post("/apply/{run_id}/cancel")
async def cancel_application(run_id: str) -> dict[str, str]:
    run = crawl_store.get_run(run_id)
    if run is None:
        return {"status": "gone"}
    from app.services.jobs.apply.browser import close_run_browser

    run.status = "cancelled"
    await close_run_browser(run)
    crawl_store.drop_run(run_id)
    return {"status": "cancelled"}


@router.get("/apply/{run_id}/screenshot")
async def apply_screenshot(run_id: str, step: int = 0) -> Response:
    path = screenshot_path(run_id, step)
    if not path.exists() and step == 0:
        # first capture may have been recorded as step 0 or 1 depending on flow
        path = screenshot_path(run_id, 1)
    if not path.exists():
        raise HTTPException(status_code=404, detail="No screenshot for this run/step yet")
    return Response(content=path.read_bytes(), media_type="image/png", headers={"Cache-Control": "no-store"})
