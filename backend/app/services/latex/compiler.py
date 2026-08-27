import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.utils.sandbox import run_sandboxed

COMPILE_TIMEOUT_SECONDS = 20.0
COMPILED_ROOT = Path(__file__).resolve().parents[3] / ".data" / "compiled"

# Section ids become filenames on disk — keep them to the same charset the
# sectioner's marker regex allows, so a crafted id can't escape the workdir.
_SAFE_ID_PATTERN = re.compile(r"^[\w-]+$")


@dataclass
class CompileResult:
    success: bool
    pdf_bytes: bytes | None
    log: str


def _run_tectonic(tex_source: str, workdir: Path, basename: str) -> CompileResult:
    workdir.mkdir(parents=True, exist_ok=True)
    tex_path = workdir / f"{basename}.tex"
    tex_path.write_text(tex_source, encoding="utf-8")

    cmd = ["tectonic", "--only-cached", "--untrusted", "-o", str(workdir), str(tex_path)]
    try:
        result = run_sandboxed(cmd, cwd=workdir, timeout=COMPILE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return CompileResult(success=False, pdf_bytes=None, log=f"Compilation timed out after {COMPILE_TIMEOUT_SECONDS}s")
    except FileNotFoundError:
        return CompileResult(success=False, pdf_bytes=None, log="tectonic is not installed on this machine")

    log = result.stdout + result.stderr
    pdf_path = workdir / f"{basename}.pdf"
    if result.returncode != 0 or not pdf_path.exists():
        return CompileResult(success=False, pdf_bytes=None, log=log)

    return CompileResult(success=True, pdf_bytes=pdf_path.read_bytes(), log=log)


def compile_latex(latex: str, session_id: str) -> CompileResult:
    return _run_tectonic(latex, COMPILED_ROOT / session_id, "resume")


def compile_fragment(fragment_latex: str, session_id: str, section_id: str) -> CompileResult:
    if not _SAFE_ID_PATTERN.match(section_id):
        return CompileResult(success=False, pdf_bytes=None, log=f"Invalid section id: {section_id!r}")
    return _run_tectonic(fragment_latex, COMPILED_ROOT / session_id / "fragments", section_id)
