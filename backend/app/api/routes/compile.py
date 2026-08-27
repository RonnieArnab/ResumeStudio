import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.models.resume import CompileResponse, SectionFragment
from app.services.latex.compiler import COMPILED_ROOT, compile_fragment, compile_latex
from app.services.latex.sectioner import parse_sections, render_fragment
from app.services.latex.validator import validate_latex
from app.services.session.models import SectionFragmentRef
from app.services.session.session_store import session_store

router = APIRouter(prefix="/api/resume", tags=["compile"])


def _compile_section_fragments(session_id: str, latex: str, version: int) -> list[SectionFragment]:
    """Best-effort: each section's content was already validated as part of
    the merged document, so a fragment failing here shouldn't block the
    overall compile — it just won't get a clickable preview yet."""
    fragments: list[SectionFragment] = []
    for section_id, body in parse_sections(latex).items():
        fragment_latex = render_fragment(body)
        result = compile_fragment(fragment_latex, session_id, section_id)
        if result.success:
            fragments.append(SectionFragment(id=section_id, pdf_url=f"/api/resume/{session_id}/sections/{section_id}/pdf?v={version}"))
    return fragments


def recompile_session(session_id: str, latex: str) -> CompileResponse:
    """Shared by the upload flow and the explicit /compile endpoint: validate
    fast-path syntax, only invoke the real compiler if that passes, and
    persist the resulting pdf_url + section fragments onto the session.

    Every successful compile gets a fresh `?v=` query param on its URLs —
    without it, the URL for a given section never changes across edits, so
    neither the browser's HTTP cache nor React's effect (keyed on the url
    prop) would notice the PDF underneath had changed."""
    # check_commands=False: this validates the *full* document, preamble
    # included, which is developer-authored and trusted — only the
    # structural (brace/environment) checks apply here. The command
    # allowlist is enforced where it matters: on agent-authored section
    # snippets, in propose_section_edit.
    validation = validate_latex(latex, check_commands=False)
    if not validation.valid:
        session_store.update_pdf_url(session_id, None)
        session_store.update_section_fragments(session_id, [])
        return CompileResponse(pdf_url=None, section_boxes=[], section_fragments=[], validation_errors=validation.errors)

    result = compile_latex(latex, session_id)
    if not result.success:
        session_store.update_pdf_url(session_id, None)
        session_store.update_section_fragments(session_id, [])
        return CompileResponse(pdf_url=None, section_boxes=[], section_fragments=[], validation_errors=[result.log[-2000:]])

    version = time.time_ns()
    pdf_url = f"/api/resume/{session_id}/pdf?v={version}"
    session_store.update_pdf_url(session_id, pdf_url)

    fragments = _compile_section_fragments(session_id, latex, version)
    session_store.update_section_fragments(session_id, [SectionFragmentRef(id=f.id, pdf_url=f.pdf_url) for f in fragments])

    return CompileResponse(pdf_url=pdf_url, section_boxes=[], section_fragments=fragments, validation_errors=[])


@router.post("/{session_id}/compile", response_model=CompileResponse)
async def compile_resume(session_id: str) -> CompileResponse:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return recompile_session(session_id, session.latex)


@router.get("/{session_id}/pdf")
async def get_resume_pdf(session_id: str) -> Response:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    pdf_path = COMPILED_ROOT / session_id / "resume.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="No compiled PDF for this session yet")

    return Response(content=pdf_path.read_bytes(), media_type="application/pdf", headers={"Cache-Control": "no-store"})


@router.get("/{session_id}/sections/{section_id}/pdf")
async def get_section_pdf(session_id: str, section_id: str) -> Response:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    pdf_path = COMPILED_ROOT / session_id / "fragments" / f"{section_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="No compiled fragment for this section yet")

    return Response(content=pdf_path.read_bytes(), media_type="application/pdf", headers={"Cache-Control": "no-store"})
