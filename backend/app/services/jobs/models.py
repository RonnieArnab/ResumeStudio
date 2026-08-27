"""Data models for the job crawler + auto-apply feature.

Split mirrors the rest of the repo: Pydantic models are the API/wire shape,
plain dataclasses hold in-process state that never leaves the server
(`ApplyRun` carries live Playwright handles, so it can't be a Pydantic model)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

Provider = Literal["greenhouse", "lever", "ashby", "linkedin", "wellfound", "other"]

SourceKind = Literal["board", "search"]

# Providers that need a signed-in browser session (see apply/connected.py).
CONNECTED_PROVIDERS: tuple[str, ...] = ("linkedin", "wellfound")

FieldKind = Literal[
    "text", "email", "tel", "url", "number", "textarea", "select", "combobox", "file", "checkbox", "radio", "unknown"
]

FieldSource = Literal["profile", "generated", "default", "empty", "user"]

RunStatus = Literal[
    "filling", "ready_for_review", "submitting", "submitted", "failed", "cancelled"
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Board sources                                                                #
# --------------------------------------------------------------------------- #


class BoardSource(BaseModel):
    id: str
    provider: Provider
    kind: SourceKind = "board"
    slug: str = ""  # board kind: the ATS board slug
    query: str = ""  # search kind: keywords
    location: str = ""  # search kind: location filter
    label: str
    added_at: datetime = Field(default_factory=_now)

    @property
    def key(self) -> str:
        """Stable prefix for the job ids this source produces."""
        if self.kind == "search":
            return f"{self.provider}:search:{self.id}"
        return f"{self.provider}:{self.slug}"


class AddSourceRequest(BaseModel):
    # Board source: a raw board URL ("boards.greenhouse.io/stripe") or "provider:slug".
    ref: str | None = None
    # Search source (LinkedIn / Wellfound): provider + keywords (+ optional location).
    provider: Provider | None = None
    query: str | None = None
    location: str | None = None
    label: str | None = None


class RegistryEntry(BaseModel):
    name: str
    provider: Provider
    slug: str


class ConnectionStatus(BaseModel):
    provider: Provider
    connected: bool
    since: datetime | None = None


class PrepareUrlRequest(BaseModel):
    url: str
    title: str | None = None
    resume_session_id: str | None = None


class AutofillProfileRequest(BaseModel):
    resume_session_id: str
    overwrite: bool = False


# --------------------------------------------------------------------------- #
# Job postings + matching                                                      #
# --------------------------------------------------------------------------- #


class JobPosting(BaseModel):
    id: str  # stable: "{provider}:{slug}:{external_id}"
    provider: Provider
    company: str
    title: str
    location: str = ""
    team: str | None = None
    remote: bool = False
    url: str = ""
    apply_url: str = ""
    description_text: str = ""
    posted_at: datetime | None = None


class MatchResult(BaseModel):
    job_id: str
    score: int = 0  # 0-100
    verdict: str = "unknown"  # strong | possible | weak | error
    summary: str = ""
    matched_requirements: list[str] = []
    missing_requirements: list[str] = []
    error: str | None = None


class RankedJob(BaseModel):
    job: JobPosting
    match: MatchResult | None = None


class CrawlRequest(BaseModel):
    resume_session_id: str | None = None
    # Optional plain-text resume/experience blurb used when no session is given.
    resume_text: str | None = None
    min_score: int = 0
    location_contains: str | None = None
    remote_only: bool = False
    # Only keep postings newer than this many days (None = any age).
    posted_within_days: int | None = None
    # The seniority the user is targeting; feeds the match prompt + a soft filter.
    target_years_experience: int | None = None


# --------------------------------------------------------------------------- #
# Applicant profile                                                            #
# --------------------------------------------------------------------------- #


class ApplicantProfile(BaseModel):
    full_name: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    work_authorization: str = ""
    requires_sponsorship: bool | None = None
    years_experience: str = ""
    pronouns: str = ""
    cover_letter_blurb: str = ""
    # keyword -> canned answer, consulted before falling back to the LLM.
    default_answers: dict[str, str] = {}
    resume_pdf_path: str | None = None
    resume_source_label: str | None = None
    updated_at: datetime | None = None


class SetProfileResumeRequest(BaseModel):
    resume_session_id: str


# --------------------------------------------------------------------------- #
# Apply runs                                                                   #
# --------------------------------------------------------------------------- #


class FormField(BaseModel):
    selector: str
    label: str
    kind: FieldKind = "text"
    options: list[str] = []
    required: bool = False
    value: str = ""
    source: FieldSource = "empty"
    # Radio groups collapse to one FormField; this maps an option label to the
    # selector of its underlying <input>. Not sent to the client.
    option_selectors: dict[str, str] = Field(default_factory=dict, exclude=True)


class ApplyStep(BaseModel):
    index: int
    title: str
    screenshot_url: str
    note: str = ""


class ApplyRunView(BaseModel):
    run_id: str
    job_id: str
    job_title: str
    company: str
    status: RunStatus
    fields: list[FormField]
    screenshot_url: str
    steps: list[ApplyStep] = []
    captcha_detected: bool = False
    manual_only: bool = False
    notes: list[str] = []
    confirmation_text: str | None = None
    created_at: datetime = Field(default_factory=_now)


class PrepareApplyRequest(BaseModel):
    job_id: str
    # Optional: resume session whose text seeds free-text answers.
    resume_session_id: str | None = None


class FieldOverridesRequest(BaseModel):
    # selector -> new value
    overrides: dict[str, str]


@dataclass
class ApplyRun:
    run_id: str
    job: JobPosting
    profile: ApplicantProfile
    status: RunStatus = "filling"
    fields: list[FormField] = field(default_factory=list)
    captcha_detected: bool = False
    # LinkedIn/Wellfound/multi-step: user finishes in the open browser window.
    manual_only: bool = False
    notes: list[str] = field(default_factory=list)
    confirmation_text: str | None = None
    # (step_index, title, note) per captured screenshot.
    step_meta: list[tuple[int, str, str]] = field(default_factory=list)
    # Live Playwright handles — present only while the run is in memory.
    page: object | None = None
    context: object | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def to_view(self, screenshot_url_for) -> ApplyRunView:
        """`screenshot_url_for(step_index) -> str` builds a cache-busted URL."""
        steps = [
            ApplyStep(index=i, title=title, screenshot_url=screenshot_url_for(i), note=note)
            for (i, title, note) in self.step_meta
        ]
        latest = steps[-1].screenshot_url if steps else screenshot_url_for(0)
        return ApplyRunView(
            run_id=self.run_id,
            job_id=self.job.id,
            job_title=self.job.title,
            company=self.job.company,
            status=self.status,
            fields=self.fields,
            screenshot_url=latest,
            steps=steps,
            captcha_detected=self.captcha_detected,
            manual_only=self.manual_only,
            notes=self.notes,
            confirmation_text=self.confirmation_text,
            created_at=self.created_at,
        )
