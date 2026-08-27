from dataclasses import dataclass, field

import jinja2

from app.services.latex.sectioner import TEMPLATES_DIR, create_latex_jinja_env

# Fixed, hardcoded structure for milestone 2 — no LLM involved yet. A line is
# assigned to a section once its text matches one of these heading keywords;
# everything before the first match is treated as the header block.
SECTION_KEYWORDS: dict[str, list[str]] = {
    "experience": ["experience", "work experience", "employment", "professional experience"],
    "education": ["education"],
    "skills": ["skills", "technical skills", "core competencies"],
    "projects": ["projects", "personal projects"],
}

SECTION_TEMPLATES: dict[str, str] = {
    "experience": "experience.tex.j2",
    "education": "education.tex.j2",
    "skills": "skills.tex.j2",
    "projects": "projects.tex.j2",
}

_LATEX_ESCAPE_MAP = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex(text: str) -> str:
    return "".join(_LATEX_ESCAPE_MAP.get(ch, ch) for ch in text)


def _match_section_keyword(line: str) -> str | None:
    normalized = line.strip().lower().strip(":")
    for section_id, keywords in SECTION_KEYWORDS.items():
        if normalized in keywords:
            return section_id
    return None


@dataclass
class ParsedResume:
    name: str = ""
    contact: str = ""
    sections: dict[str, list[str]] = field(default_factory=dict)


def parse_resume_text(raw_text: str) -> ParsedResume:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    parsed = ParsedResume()
    current_section: str | None = None
    header_lines: list[str] = []

    for line in lines:
        keyword_match = _match_section_keyword(line)
        if keyword_match:
            current_section = keyword_match
            parsed.sections.setdefault(current_section, [])
            continue

        if current_section is None:
            header_lines.append(line)
        else:
            parsed.sections[current_section].append(line)

    if header_lines:
        parsed.name = header_lines[0]
        parsed.contact = " | ".join(header_lines[1:])

    return parsed


def render_sections(parsed: ParsedResume, env: jinja2.Environment | None = None) -> dict[str, str]:
    env = env or create_latex_jinja_env(TEMPLATES_DIR / "sections")

    rendered: dict[str, str] = {
        "header": env.get_template("header.tex.j2").render(
            name=escape_latex(parsed.name) or "Your Name",
            contact=escape_latex(parsed.contact),
        )
    }

    for section_id, template_name in SECTION_TEMPLATES.items():
        lines = parsed.sections.get(section_id, [])
        if not lines:
            continue
        template = env.get_template(template_name)
        rendered[section_id] = template.render(lines=[escape_latex(line) for line in lines])

    return rendered
