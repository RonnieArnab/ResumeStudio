import json
from typing import Any


def format_sse(event: dict[str, Any]) -> str:
    event_type = event.get("type", "message")
    return f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
