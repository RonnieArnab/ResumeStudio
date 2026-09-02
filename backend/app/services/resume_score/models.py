"""Wire models for the resume ⇄ job-description match report."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

RequirementStatus = Literal["met", "partial", "missing"]
Priority = Literal["high", "medium", "low"]
Verdict = Literal["strong", "moderate", "weak"]


class ScoreDimension(BaseModel):
    key: str
    label: str
    score: int = Field(ge=0, le=100)
    weight: float = 1.0
    note: str = ""


class KeywordAnalysis(BaseModel):
    coverage: int = Field(ge=0, le=100)  # % of JD keywords found in the resume
    matched: list[str] = []
    partial: list[str] = []
    missing: list[str] = []


class RequirementMatch(BaseModel):
    requirement: str
    status: RequirementStatus
    evidence: str = ""


class Suggestion(BaseModel):
    section: str = ""  # section id if it maps to one, else ""
    title: str
    detail: str = ""
    priority: Priority = "medium"


class MatchReport(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    verdict: Verdict
    headline: str
    summary: str
    dimensions: list[ScoreDimension] = []
    keywords: KeywordAnalysis
    requirements: list[RequirementMatch] = []
    strengths: list[str] = []
    gaps: list[str] = []
    suggestions: list[Suggestion] = []
    jd_title: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MatchReportRequest(BaseModel):
    job_description: str
