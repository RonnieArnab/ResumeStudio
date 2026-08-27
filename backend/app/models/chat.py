from datetime import datetime

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    text: str
    job_description: str | None = None


class ChatMessageSummary(BaseModel):
    role: str
    text: str
    created_at: datetime
