from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.chat import ChatMessageRequest, ChatMessageSummary
from app.services.agent.orchestrator import run_chat_message
from app.services.agent.streaming import format_sse
from app.services.session.session_store import session_store

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{session_id}/message")
async def send_chat_message(session_id: str, body: ChatMessageRequest) -> StreamingResponse:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_stream():
        async for event in run_chat_message(session_id, body.text, body.job_description):
            yield format_sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{session_id}/history", response_model=list[ChatMessageSummary])
async def get_chat_history(session_id: str) -> list[ChatMessageSummary]:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return [ChatMessageSummary(role=m.role, text=m.text, created_at=m.created_at) for m in session.chat_history]
