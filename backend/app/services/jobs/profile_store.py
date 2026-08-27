"""Applicant profile persistence.

Unlike resume sessions (in-memory, per-upload), the profile is written to a
JSON file so it survives restarts — the user fills it in once."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.services.jobs.models import ApplicantProfile
from app.services.jobs.storage import PROFILE_PATH


def load_profile() -> ApplicantProfile:
    if not PROFILE_PATH.exists():
        return ApplicantProfile()
    try:
        return ApplicantProfile.model_validate_json(PROFILE_PATH.read_text())
    except (ValueError, OSError):
        return ApplicantProfile()


def save_profile(profile: ApplicantProfile) -> ApplicantProfile:
    # Keep first/last and full name mutually consistent when only one is given.
    if profile.full_name and not (profile.first_name or profile.last_name):
        parts = profile.full_name.split()
        profile.first_name = parts[0] if parts else ""
        profile.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
    if not profile.full_name and (profile.first_name or profile.last_name):
        profile.full_name = f"{profile.first_name} {profile.last_name}".strip()

    profile.updated_at = datetime.now(timezone.utc)
    PROFILE_PATH.write_text(profile.model_dump_json(indent=2))
    return profile
