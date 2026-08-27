import re
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.routes.compile import recompile_session
from app.models.resume import ResumeUploadResponse, ResumeSessionResponse, SectionFragment, SectionSummary
from app.services.latex.sectioner import (
    TEMPLATES_DIR,
    create_latex_jinja_env,
    list_sections,
    parse_sections,
    render_document,
)
from app.services.resume_parser.docx_to_text import extract_text_from_docx
from app.services.resume_parser.pdf_to_text import extract_text_from_pdf
from app.services.resume_parser.text_to_latex import parse_resume_text, render_sections
from app.services.session.models import ResumeSession
from app.services.session.session_store import session_store

router = APIRouter(prefix="/api/resume", tags=["resume"])

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def _extension_of(filename: str) -> str:
    return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)) -> ResumeUploadResponse:
    extension = _extension_of(file.filename or "")
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .pdf and .docx files are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    raw_text = extract_text_from_pdf(file_bytes) if extension == ".pdf" else extract_text_from_docx(file_bytes)
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract any text from the uploaded file")

    parsed = parse_resume_text(raw_text)
    section_env = create_latex_jinja_env(TEMPLATES_DIR / "sections")
    rendered_sections = render_sections(parsed, section_env)
    latex = render_document(rendered_sections)

    session = session_store.create(ResumeSession(session_id=str(uuid.uuid4()), latex=latex))
    recompile_session(session.session_id, session.latex)

    sections = [SectionSummary(**s) for s in list_sections(session.latex)]
    fragments = [SectionFragment(id=f.id, pdf_url=f.pdf_url) for f in session.section_fragments]
    return ResumeUploadResponse(
        session_id=session.session_id, latex=session.latex, sections=sections, pdf_url=session.pdf_url, section_fragments=fragments
    )


def _session_response(session) -> ResumeSessionResponse:
    sections = [SectionSummary(**s) for s in list_sections(session.latex)]
    fragments = [SectionFragment(id=f.id, pdf_url=f.pdf_url) for f in session.section_fragments]
    return ResumeSessionResponse(
        session_id=session.session_id,
        latex=session.latex,
        sections=sections,
        pdf_url=session.pdf_url,
        section_fragments=fragments,
    )


@router.get("/{session_id}", response_model=ResumeSessionResponse)
async def get_resume(session_id: str) -> ResumeSessionResponse:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_response(session)


class AddSectionRequest(BaseModel):
    title: str


_NEW_SECTION_BODY = (
    "\\section{{{title}}}\n"
    "\\begin{{itemize}}[leftmargin=*,label=\\textbullet,itemsep=2pt,parsep=0pt]\n"
    "\\resumeItem{{Add your first item here — then click the section to have the agent expand it.}}\n"
    "\\end{{itemize}}"
)


@router.post("/{session_id}/sections", response_model=ResumeSessionResponse)
async def add_section(session_id: str, body: AddSectionRequest) -> ResumeSessionResponse:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Section title is required")

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "section"
    sections = parse_sections(session.latex)
    if slug in sections:
        n = 2
        while f"{slug}-{n}" in sections:
            n += 1
        slug = f"{slug}-{n}"

    sections[slug] = _NEW_SECTION_BODY.format(title=title)
    new_latex = render_document(sections)
    session_store.update_latex(session_id, new_latex)
    recompile_session(session_id, new_latex)
    return _session_response(session_store.get(session_id))


@router.delete("/{session_id}/sections/{section_id}", response_model=ResumeSessionResponse)
async def delete_section(session_id: str, section_id: str) -> ResumeSessionResponse:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if section_id == "header":
        raise HTTPException(status_code=400, detail="The header can't be removed")

    sections = parse_sections(session.latex)
    if section_id not in sections:
        raise HTTPException(status_code=404, detail="Section not found")
    del sections[section_id]

    new_latex = render_document(sections)
    session_store.update_latex(session_id, new_latex)
    recompile_session(session_id, new_latex)
    return _session_response(session_store.get(session_id))
