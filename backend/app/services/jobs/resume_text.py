"""Turn the session's LaTeX resume into plain text for LLM prompts.

Deliberately crude — the goal is readable prose for a model, not a faithful
de-render. Reuses nothing from the LaTeX services because those operate on
structured section markers, not flattened text."""

from __future__ import annotations

import re

_COMMENT_RE = re.compile(r"(?<!\\)%.*$", re.MULTILINE)
_SECTION_MARKER_RE = re.compile(r"%\s*\[SECTION:[^\]]*\]", re.IGNORECASE)
_COMMAND_WITH_ARG_RE = re.compile(r"\\(?:textbf|textit|emph|underline|section|subsection|sectionheading|href|textrm)\*?\s*\{")
_BARE_COMMAND_RE = re.compile(r"\\[a-zA-Z@]+\*?")
_BRACES_RE = re.compile(r"[{}]")
_WS_RE = re.compile(r"[ \t]+")
_BLANKS_RE = re.compile(r"\n\s*\n\s*\n+")

_UNESCAPE = {
    r"\&": "&",
    r"\%": "%",
    r"\$": "$",
    r"\#": "#",
    r"\_": "_",
    r"\{": "{",
    r"\}": "}",
    r"\textbackslash{}": "\\",
    r"\textasciitilde{}": "~",
    r"\textasciicircum{}": "^",
    r"~": " ",
    r"\\": "\n",
    r"\item": "- ",
}


def latex_to_plain_text(latex: str) -> str:
    text = _SECTION_MARKER_RE.sub("", latex)
    text = _COMMENT_RE.sub("", text)
    for src, dst in _UNESCAPE.items():
        text = text.replace(src, dst)
    text = _COMMAND_WITH_ARG_RE.sub("{", text)
    text = _BARE_COMMAND_RE.sub(" ", text)
    text = _BRACES_RE.sub("", text)
    text = _WS_RE.sub(" ", text)
    text = _BLANKS_RE.sub("\n\n", text)
    return text.strip()
