import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings
from app.services.agent.prompts import JD_TAILORING_SYSTEM_PROMPT, SECTION_EDIT_SYSTEM_PROMPT
from app.services.agent.tools import JD_TAILORING_TOOLS, SECTION_EDIT_TOOLS, execute_tool
from app.services.latex.sectioner import parse_sections
from app.services.session.session_store import session_store

MAX_STEPS = 8
MODEL = "gpt-4o-mini"


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


async def _run_tool_loop(session_id: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AsyncIterator[dict[str, Any]]:
    client = _client()

    for _step in range(MAX_STEPS):
        response = await client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
        message = response.choices[0].message

        assistant_msg: dict[str, Any] = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ]
        messages.append(assistant_msg)

        if not message.tool_calls:
            yield {"type": "done", "message": message.content or ""}
            return

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            yield {"type": "tool_call", "name": name, "arguments": args}
            result = execute_tool(session_id, name, args)
            yield {"type": "tool_result", "name": name, "result": result}

            if name == "propose_section_edit":
                if result.get("staged"):
                    yield {"type": "section_proposed", "section_id": result["section_id"]}
                else:
                    yield {"type": "validation_error", "errors": result.get("errors", [])}

            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})

    yield {"type": "done", "message": "Reached the step limit without finishing."}


async def run_section_edit(session_id: str, section_id: str, instruction: str) -> AsyncIterator[dict[str, Any]]:
    session = session_store.get(session_id)
    if session is None:
        yield {"type": "error", "message": "Session not found"}
        return

    sections = parse_sections(session.latex)
    if section_id not in sections:
        yield {"type": "error", "message": f"Unknown section: {section_id}"}
        return

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SECTION_EDIT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Full resume (for cross-section context):\n{session.latex}\n\n"
                f"The user selected the '{section_id}' section, currently:\n{sections[section_id]}\n\n"
                f"User instruction: {instruction}"
            ),
        },
    ]

    async for event in _run_tool_loop(session_id, messages, SECTION_EDIT_TOOLS):
        yield event


async def run_chat_message(session_id: str, text: str, job_description: str | None) -> AsyncIterator[dict[str, Any]]:
    session = session_store.get(session_id)
    if session is None:
        yield {"type": "error", "message": "Session not found"}
        return

    if job_description is not None:
        session_store.update_job_description(session_id, job_description)
        session = session_store.get(session_id)
        assert session is not None

    jd_context = f"Job description:\n{session.job_description}\n\n" if session.job_description else ""

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": JD_TAILORING_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Full resume:\n{session.latex}\n\n{jd_context}User message: {text}",
        },
    ]

    session_store.append_chat_message(session_id, "user", text)

    final_message = ""
    async for event in _run_tool_loop(session_id, messages, JD_TAILORING_TOOLS):
        if event["type"] == "done":
            final_message = event.get("message", "")
        yield event

    session_store.append_chat_message(session_id, "agent", final_message)
