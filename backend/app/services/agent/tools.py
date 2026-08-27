from typing import Any, Callable

from app.services.latex.sectioner import list_sections, parse_sections
from app.services.latex.validator import validate_latex
from app.services.session.session_store import session_store

_LIST_SECTIONS = {
    "type": "function",
    "function": {
        "name": "list_sections",
        "description": "List all section ids in the resume with a short summary of each.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

_GET_SECTION = {
    "type": "function",
    "function": {
        "name": "get_section",
        "description": "Get the raw LaTeX body of one section by id.",
        "parameters": {
            "type": "object",
            "properties": {"section_id": {"type": "string"}},
            "required": ["section_id"],
        },
    },
}

_GET_FULL_RESUME = {
    "type": "function",
    "function": {
        "name": "get_full_resume",
        "description": "Get the full section-tagged LaTeX document, for cross-section consistency checks.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

_GET_JOB_DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "get_job_description",
        "description": "Get the job description text currently attached to this session, if any.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

_VALIDATE_LATEX = {
    "type": "function",
    "function": {
        "name": "validate_latex",
        "description": "Run a LaTeX snippet through the fast syntax validator. Returns any errors found; empty list means valid.",
        "parameters": {
            "type": "object",
            "properties": {"latex_snippet": {"type": "string"}},
            "required": ["latex_snippet"],
        },
    },
}

_PROPOSE_SECTION_EDIT = {
    "type": "function",
    "function": {
        "name": "propose_section_edit",
        "description": (
            "Stage an edit to one section for the user to review. Does not apply the edit — the user must "
            "accept it. The server re-validates new_latex before staging; if invalid, fix the errors and call "
            "this again. Call this once per section you want to change; you may call it for multiple sections "
            "in the same run when tailoring to a job description."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "section_id": {"type": "string"},
                "new_latex": {
                    "type": "string",
                    "description": "The complete new LaTeX body for this section, without % [SECTION:] markers.",
                },
                "rationale": {"type": "string", "description": "Short explanation of what changed and why."},
            },
            "required": ["section_id", "new_latex", "rationale"],
        },
    },
}

_DIFF_SUMMARY = {
    "type": "function",
    "function": {
        "name": "diff_summary",
        "description": "Get a structured summary of every section edit staged so far in this run.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

# Milestone 5: single-section edits driven by a section click. Kept to the
# minimal tool set the task actually needs.
SECTION_EDIT_TOOLS: list[dict[str, Any]] = [
    _LIST_SECTIONS,
    _GET_SECTION,
    _GET_FULL_RESUME,
    _VALIDATE_LATEX,
    _PROPOSE_SECTION_EDIT,
]

# Milestone 6: JD tailoring may touch several sections in one run and needs
# to read the JD and summarize everything it's staged.
JD_TAILORING_TOOLS: list[dict[str, Any]] = [
    _LIST_SECTIONS,
    _GET_SECTION,
    _GET_FULL_RESUME,
    _GET_JOB_DESCRIPTION,
    _VALIDATE_LATEX,
    _PROPOSE_SECTION_EDIT,
    _DIFF_SUMMARY,
]


def _tool_list_sections(session_id: str) -> dict[str, Any]:
    session = session_store.get(session_id)
    assert session is not None
    return {"sections": list_sections(session.latex)}


def _tool_get_section(session_id: str, section_id: str = "") -> dict[str, Any]:
    session = session_store.get(session_id)
    assert session is not None
    sections = parse_sections(session.latex)
    if section_id not in sections:
        return {"error": f"Unknown section_id: {section_id}"}
    return {"section_id": section_id, "latex": sections[section_id]}


def _tool_get_full_resume(session_id: str) -> dict[str, Any]:
    session = session_store.get(session_id)
    assert session is not None
    return {"latex": session.latex}


def _tool_get_job_description(session_id: str) -> dict[str, Any]:
    session = session_store.get(session_id)
    assert session is not None
    return {"job_description": session.job_description}


def _tool_validate_latex(session_id: str, latex_snippet: str = "") -> dict[str, Any]:
    result = validate_latex(latex_snippet)
    return {"valid": result.valid, "errors": result.errors}


def _tool_propose_section_edit(session_id: str, section_id: str = "", new_latex: str = "", rationale: str = "") -> dict[str, Any]:
    validation = validate_latex(new_latex)
    if not validation.valid:
        return {"staged": False, "errors": validation.errors}

    # Syntax validity alone doesn't catch a model quietly dropping the
    # section's own heading command (still-valid LaTeX, but the rendered
    # PDF would lose that section's bold title). Require it stay present
    # whenever the original section had one.
    session = session_store.get(session_id)
    assert session is not None
    old_body = parse_sections(session.latex).get(section_id, "")
    if "\\sectionheading{" in old_body and "\\sectionheading{" not in new_latex:
        return {
            "staged": False,
            "errors": ["The edited section is missing \\sectionheading{...} — keep the original heading command unless explicitly asked to rename it."],
        }

    session_store.stage_edit(session_id, section_id, new_latex, rationale)
    return {"staged": True, "section_id": section_id}


def _tool_diff_summary(session_id: str) -> dict[str, Any]:
    session = session_store.get(session_id)
    assert session is not None
    sections = parse_sections(session.latex)
    return {
        "staged_edits": [
            {
                "section_id": edit.section_id,
                "old_latex": sections.get(edit.section_id, ""),
                "new_latex": edit.new_latex,
                "rationale": edit.rationale,
            }
            for edit in session.staged_edits.values()
        ]
    }


_HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {
    "list_sections": _tool_list_sections,
    "get_section": _tool_get_section,
    "get_full_resume": _tool_get_full_resume,
    "get_job_description": _tool_get_job_description,
    "validate_latex": _tool_validate_latex,
    "propose_section_edit": _tool_propose_section_edit,
    "diff_summary": _tool_diff_summary,
}


def execute_tool(session_id: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    handler = _HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    return handler(session_id, **args)
