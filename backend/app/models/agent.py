from pydantic import BaseModel


class SectionEditRequest(BaseModel):
    section_id: str
    instruction: str


class DiffActionRequest(BaseModel):
    section_ids: list[str]


class StagedEditSummary(BaseModel):
    section_id: str
    old_latex: str
    new_latex: str
    rationale: str
