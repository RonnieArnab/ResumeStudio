from pydantic import BaseModel


class SectionSummary(BaseModel):
    id: str
    summary: str


class SectionFragment(BaseModel):
    id: str
    pdf_url: str


class ResumeUploadResponse(BaseModel):
    session_id: str
    latex: str
    sections: list[SectionSummary]
    pdf_url: str | None = None
    section_fragments: list[SectionFragment] = []


class ResumeSessionResponse(ResumeUploadResponse):
    pass


class SectionBox(BaseModel):
    """Reserved for a future true-SyncTeX overlay on the single merged PDF.
    Left empty by the fragment-render approach used for section-click
    mapping today."""

    id: str
    page: int
    x: float
    y: float
    width: float
    height: float


class CompileResponse(BaseModel):
    pdf_url: str | None
    section_boxes: list[SectionBox] = []
    section_fragments: list[SectionFragment] = []
    validation_errors: list[str] = []
