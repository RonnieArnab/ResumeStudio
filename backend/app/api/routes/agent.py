from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.routes.compile import recompile_session
from app.models.agent import DiffActionRequest, SectionEditRequest, StagedEditSummary
from app.models.resume import CompileResponse
from app.services.agent.orchestrator import run_section_edit
from app.services.agent.streaming import format_sse
from app.services.latex.patcher import apply_section_patch
from app.services.latex.sectioner import parse_sections
from app.services.session.session_store import session_store

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/{session_id}/section-edit")
async def section_edit(session_id: str, body: SectionEditRequest) -> StreamingResponse:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_stream():
        async for event in run_section_edit(session_id, body.section_id, body.instruction):
            yield format_sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{session_id}/diff", response_model=list[StagedEditSummary])
async def list_staged_diffs(session_id: str) -> list[StagedEditSummary]:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    sections = parse_sections(session.latex)
    return [
        StagedEditSummary(section_id=sid, old_latex=sections.get(sid, ""), new_latex=edit.new_latex, rationale=edit.rationale)
        for sid, edit in session.staged_edits.items()
    ]


@router.get("/{session_id}/diff/{section_id}", response_model=StagedEditSummary)
async def get_staged_diff(session_id: str, section_id: str) -> StagedEditSummary:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    edit = session.staged_edits.get(section_id)
    if edit is None:
        raise HTTPException(status_code=404, detail="No staged edit for this section")

    sections = parse_sections(session.latex)
    return StagedEditSummary(section_id=section_id, old_latex=sections.get(section_id, ""), new_latex=edit.new_latex, rationale=edit.rationale)


@router.post("/{session_id}/diff/apply", response_model=CompileResponse)
async def apply_diff(session_id: str, body: DiffActionRequest) -> CompileResponse:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    latex = session.latex
    applied: list[str] = []
    for section_id in body.section_ids:
        edit = session.staged_edits.get(section_id)
        if edit is None:
            continue
        latex = apply_section_patch(latex, section_id, edit.new_latex)
        applied.append(section_id)

    session_store.update_latex(session_id, latex)
    for section_id in applied:
        session_store.clear_staged_edit(session_id, section_id)

    return recompile_session(session_id, latex)


@router.post("/{session_id}/diff/reject")
async def reject_diff(session_id: str, body: DiffActionRequest) -> dict[str, list[str]]:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    for section_id in body.section_ids:
        session_store.clear_staged_edit(session_id, section_id)

    return {"rejected": body.section_ids}
