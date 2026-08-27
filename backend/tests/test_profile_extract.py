"""Profile extraction: regex fallbacks + never trusting an invented URL."""

import pytest

from app.services.jobs import profile_extract
from app.services.jobs.models import ApplicantProfile


def test_regex_fallback_pulls_contacts():
    text = "Jane Doe  jane.doe+cv@example.com  github.com/janedoe  linkedin.com/in/jane-doe"
    got = profile_extract._regex_fallback(text)
    assert got["email"] == "jane.doe+cv@example.com"
    assert got["github_url"] == "https://github.com/janedoe"
    assert got["linkedin_url"].endswith("/in/jane-doe")


def test_strip_latex_comments_drops_preamble_and_comment_lines():
    latex = "% (https://github.com/sb2nov/resume)\n\\begin{document}\n\\name{Real Person}\n% note\nbody\n"
    out = profile_extract._strip_latex_comments(latex)
    assert "sb2nov" not in out
    assert "Real Person" in out
    assert "note" not in out


async def test_extract_rejects_url_not_in_resume(monkeypatch):
    # LLM invents a github handle that appears nowhere in the resume
    async def fake_create(**_):
        class R:
            choices = [type("C", (), {"message": type("M", (), {"content": '{"github_url": "https://github.com/sb2nov"}'})})]

        return R()

    monkeypatch.setenv("OPENAI_API_KEY", "x")
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(
        profile_extract, "AsyncOpenAI", lambda **_: type("X", (), {"chat": type("Y", (), {"completions": type("Z", (), {"create": staticmethod(fake_create)})})})()
    )
    fields = await profile_extract.extract_profile_fields("Arnab Ghosh — backend engineer", raw_latex="\\begin{document}\\name{Arnab}")
    assert not fields.get("github_url")
    get_settings.cache_clear()


def test_apply_extracted_only_fills_blanks_unless_overwrite():
    p = ApplicantProfile(full_name="Set By User", email="")
    profile_extract.apply_extracted(p, {"full_name": "From Resume", "email": "a@b.com"})
    assert p.full_name == "Set By User"  # not overwritten
    assert p.email == "a@b.com"  # blank filled

    profile_extract.apply_extracted(p, {"full_name": "From Resume"}, overwrite=True)
    assert p.full_name == "From Resume"
