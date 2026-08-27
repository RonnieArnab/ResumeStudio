"""Filesystem layout for job-feature artifacts. Mirrors the `.data/` root the
LaTeX compiler already uses (see `services/latex/compiler.py`)."""

from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parents[3] / ".data"
JOBS_DIR = DATA_ROOT / "jobs"
APPLY_SHOTS_DIR = JOBS_DIR / "apply"
RESUME_DIR = JOBS_DIR / "resumes"
PROFILE_PATH = JOBS_DIR / "profile.json"

for _d in (JOBS_DIR, APPLY_SHOTS_DIR, RESUME_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def screenshot_path(run_id: str) -> Path:
    return APPLY_SHOTS_DIR / f"{run_id}.png"
