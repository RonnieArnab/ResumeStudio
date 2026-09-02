"""PUT /api/resume/{id}/latex — full-document hand edits: fast structural
rejection, persistence regardless of compiler outcome, and surfaced compile
errors."""

import uuid

import pytest
from fastapi import HTTPException

from app.api.routes import resume as resume_routes
from app.models.resume import CompileResponse
from app.services.session.models import ResumeSession
from app.services.session.session_store import session_store

VALID = (
    "\\documentclass{article}\n"
    "\\begin{document}\n"
    "% [SECTION:header]\n\\name{Jane Doe}\n% [/SECTION:header]\n"
    "\\end{document}\n"
)


@pytest.fixture
def session():
    s = session_store.create(ResumeSession(session_id=str(uuid.uuid4()), latex=VALID))
    yield s
    session_store._sessions.pop(s.session_id, None)


def _fake_recompile(errors):
    return lambda _sid, _latex: CompileResponse(pdf_url=None, validation_errors=errors)


async def test_update_latex_saves_and_reports_clean_compile(session, monkeypatch):
    monkeypatch.setattr(resume_routes, "recompile_session", _fake_recompile([]))
    res = await resume_routes.update_resume_latex(
        session.session_id, resume_routes.UpdateLatexRequest(latex=VALID + "% edited\n")
    )
    assert res.compile_errors == []
    assert "% edited" in session_store.get(session.session_id).latex


async def test_update_latex_rejects_unbalanced_braces(session):
    with pytest.raises(HTTPException) as exc:
        await resume_routes.update_resume_latex(
            session.session_id, resume_routes.UpdateLatexRequest(latex="\\documentclass{article}{")
        )
    assert exc.value.status_code == 422
    # the bad edit was not persisted
    assert session_store.get(session.session_id).latex == VALID


async def test_update_latex_rejects_empty(session):
    with pytest.raises(HTTPException) as exc:
        await resume_routes.update_resume_latex(
            session.session_id, resume_routes.UpdateLatexRequest(latex="   ")
        )
    assert exc.value.status_code == 400


async def test_update_latex_surfaces_compiler_errors(session, monkeypatch):
    monkeypatch.setattr(resume_routes, "recompile_session", _fake_recompile(["! Undefined control sequence \\foo"]))
    res = await resume_routes.update_resume_latex(
        session.session_id, resume_routes.UpdateLatexRequest(latex=VALID + "\\foo\n")
    )
    assert res.compile_errors and "Undefined" in res.compile_errors[0]
    # still saved despite the compile failure
    assert "\\foo" in session_store.get(session.session_id).latex


async def test_update_latex_unknown_session(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        await resume_routes.update_resume_latex("nope", resume_routes.UpdateLatexRequest(latex=VALID))
    assert exc.value.status_code == 404
