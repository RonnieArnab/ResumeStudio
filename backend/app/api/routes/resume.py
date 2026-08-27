import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.routes.compile import recompile_session
from app.models.resume import ResumeUploadResponse, ResumeSessionResponse, SectionFragment, SectionSummary
from app.services.latex.sectioner import TEMPLATES_DIR, create_latex_jinja_env, list_sections, render_document
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


@router.get("/{session_id}", response_model=ResumeSessionResponse)
async def get_resume(session_id: str) -> ResumeSessionResponse:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    sections = [SectionSummary(**s) for s in list_sections(session.latex)]
    fragments = [SectionFragment(id=f.id, pdf_url=f.pdf_url) for f in session.section_fragments]
    return ResumeSessionResponse(
        session_id=session.session_id, latex=session.latex, sections=sections, pdf_url=session.pdf_url, section_fragments=fragments
    )
