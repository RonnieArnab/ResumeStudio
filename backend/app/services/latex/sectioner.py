import re
from pathlib import Path

import jinja2

BACKEND_DIR = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = BACKEND_DIR / "latex_templates"

SECTION_PATTERN = re.compile(
    r"% \[SECTION:(?P<id>[\w-]+)\]\n(?P<body>.*?)\n% \[/SECTION:(?P=id)\]",
    re.DOTALL,
)


def create_latex_jinja_env(directory: Path) -> jinja2.Environment:
    """Jinja2 env with LaTeX-safe delimiters so `{...}` in templates isn't
    mistaken for Jinja syntax."""
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(directory)),
        block_start_string="\\BLOCK{",
        block_end_string="}",
        variable_start_string="\\VAR{",
        variable_end_string="}",
        comment_start_string="\\#{",
        comment_end_string="}",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )


def tag_section(section_id: str, body: str) -> str:
    return f"% [SECTION:{section_id}]\n{body.strip()}\n% [/SECTION:{section_id}]"


def assemble_sections_body(sections: dict[str, str]) -> str:
    return "\n\n".join(tag_section(section_id, body) for section_id, body in sections.items())


def render_document(sections: dict[str, str]) -> str:
    env = create_latex_jinja_env(TEMPLATES_DIR)
    base_template = env.get_template("base_template.tex")
    return base_template.render(sections_body=assemble_sections_body(sections))


def render_fragment(section_body: str) -> str:
    env = create_latex_jinja_env(TEMPLATES_DIR)
    fragment_template = env.get_template("fragment_template.tex")
    return fragment_template.render(section_body=section_body.strip())


def parse_sections(tagged_latex: str) -> dict[str, str]:
    return {match.group("id"): match.group("body").strip() for match in SECTION_PATTERN.finditer(tagged_latex)}


def list_sections(tagged_latex: str) -> list[dict[str, str]]:
    summaries = []
    for section_id, body in parse_sections(tagged_latex).items():
        first_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
        summaries.append({"id": section_id, "summary": first_line[:80]})
    return summaries
