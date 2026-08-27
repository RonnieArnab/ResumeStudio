from datetime import datetime, timezone

from app.services.session.models import ChatMessage, ResumeSession, SectionFragmentRef, StagedEdit


class SessionStore:
    """In-memory session state. Swap for Redis once multi-worker deployment
    is needed — the interface is deliberately small so that's a drop-in."""

    def __init__(self) -> None:
        self._sessions: dict[str, ResumeSession] = {}

    def create(self, session: ResumeSession) -> ResumeSession:
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> ResumeSession | None:
        return self._sessions.get(session_id)

    def update_latex(self, session_id: str, latex: str) -> ResumeSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.latex = latex
        session.updated_at = datetime.now(timezone.utc)
        return session

    def update_pdf_url(self, session_id: str, pdf_url: str | None) -> ResumeSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.pdf_url = pdf_url
        session.updated_at = datetime.now(timezone.utc)
        return session

    def update_section_fragments(self, session_id: str, fragments: list[SectionFragmentRef]) -> ResumeSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.section_fragments = fragments
        session.updated_at = datetime.now(timezone.utc)
        return session

    def stage_edit(self, session_id: str, section_id: str, new_latex: str, rationale: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.staged_edits[section_id] = StagedEdit(section_id=section_id, new_latex=new_latex, rationale=rationale)
        session.updated_at = datetime.now(timezone.utc)

    def clear_staged_edit(self, session_id: str, section_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.staged_edits.pop(section_id, None)
        session.updated_at = datetime.now(timezone.utc)

    def update_job_description(self, session_id: str, job_description: str | None) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.job_description = job_description
        session.updated_at = datetime.now(timezone.utc)

    def append_chat_message(self, session_id: str, role: str, text: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.chat_history.append(ChatMessage(role=role, text=text))
        session.updated_at = datetime.now(timezone.utc)


session_store = SessionStore()
