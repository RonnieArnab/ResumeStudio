from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SectionFragmentRef:
    id: str
    pdf_url: str


@dataclass
class StagedEdit:
    section_id: str
    new_latex: str
    rationale: str


@dataclass
class ChatMessage:
    role: str  # "user" | "agent"
    text: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ResumeSession:
    session_id: str
    latex: str
    pdf_url: str | None = None
    section_fragments: list[SectionFragmentRef] = field(default_factory=list)
    staged_edits: dict[str, StagedEdit] = field(default_factory=dict)
    job_description: str | None = None
    chat_history: list[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
