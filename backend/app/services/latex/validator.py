import re
from dataclasses import dataclass, field

# Commands defined in latex_templates/base_template.tex's preamble, plus the
# small set of standard LaTeX commands that preamble/templates rely on.
# Anything else is rejected before it ever reaches the (slower) full
# compiler — catches most agent mistakes in milliseconds.
ALLOWED_COMMANDS = {
    "documentclass",
    "usepackage",
    "pagestyle",
    "setlength",
    "parindent",
    "newcommand",
    "begin",
    "end",
    "item",
    "name",
    "contact",
    "section",
    "resumeItem",
    "resumeSubItem",
    "resumeSubheading",
    "resumeSubSubheading",
    "resumeProjectHeading",
    "resumeSubHeadingListStart",
    "resumeSubHeadingListEnd",
    "resumeItemListStart",
    "resumeItemListEnd",
    "textbf",
    "textit",
    "textbackslash",
    "textasciitilde",
    "textasciicircum",
    "LARGE",
    "Large",
    "large",
    "Huge",
    "scshape",
    "small",
    "bfseries",
    "hfill",
    "hrule",
    "noindent",
    "vspace",
    "textbullet",
    "href",
}

COMMAND_PATTERN = re.compile(r"\\([a-zA-Z]+)")
ENV_TOKEN_PATTERN = re.compile(r"\\(begin|end)\{([^}]*)\}")


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def _check_braces(latex: str) -> list[str]:
    depth = 0
    for ch in latex:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return ["Unbalanced braces: an unmatched '}' was found"]
    return ["Unbalanced braces: missing closing '}'"] if depth > 0 else []


def _check_environments(latex: str) -> list[str]:
    errors: list[str] = []
    stack: list[str] = []
    for kind, name in ENV_TOKEN_PATTERN.findall(latex):
        if kind == "begin":
            stack.append(name)
        elif not stack or stack[-1] != name:
            errors.append(f"\\end{{{name}}} does not match the most recent \\begin")
        else:
            stack.pop()
    if stack:
        errors.append(f"Unclosed environment(s): {', '.join(stack)}")
    return errors


def _check_known_commands(latex: str) -> list[str]:
    used = {cmd for cmd in COMMAND_PATTERN.findall(latex)}
    unknown = sorted(used - ALLOWED_COMMANDS)
    return [f"Unknown/disallowed command(s): {', '.join(f'\\{c}' for c in unknown)}"] if unknown else []


def validate_latex(latex_snippet: str, check_commands: bool = True) -> ValidationResult:
    """check_commands gates the section-body command allowlist. It should
    stay on when validating agent-authored section snippets (the whole
    point is constraining what the model can write), but off when doing a
    structural pre-compile check of the *full* document — the preamble is
    developer-authored and trusted, and legitimately uses far more LaTeX
    commands than a section body ever should."""
    errors = [
        *_check_braces(latex_snippet),
        *_check_environments(latex_snippet),
        *(_check_known_commands(latex_snippet) if check_commands else []),
    ]
    return ValidationResult(valid=not errors, errors=errors)
