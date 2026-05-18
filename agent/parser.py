"""Parse LLM responses into agent actions."""

from __future__ import annotations

import json
import re
from typing import Any


FALLBACK_ACTION = {
    "type": "stop",
    "answer": "LLM response parsing failed.",
    "reason": "Invalid JSON output",
}


def _strip_code_fence(text: str) -> str:
    """Extract JSON only when the whole response is a fenced block."""
    fence = re.fullmatch(r"\s*```(?:json)?\s*(.*?)```\s*", text, flags=re.IGNORECASE | re.DOTALL)
    return fence.group(1).strip() if fence else text.strip()


def _extract_json_object(text: str) -> str:
    """Return the most likely JSON object substring."""
    stripped = _strip_code_fence(text)
    decoder = json.JSONDecoder()
    for match in re.finditer(r"{", stripped):
        try:
            _, end = decoder.raw_decode(stripped[match.start() :])
            return stripped[match.start() : match.start() + end]
        except json.JSONDecodeError:
            continue
    return stripped


def parse_action(raw_response: str) -> dict[str, Any]:
    """Parse a command or stop action, falling back to a stop action on failure."""
    try:
        candidate = _extract_json_object(raw_response)
        action = json.loads(candidate)
        if not isinstance(action, dict):
            return FALLBACK_ACTION.copy()
        if action.get("type") == "command" and isinstance(action.get("command"), str):
            return action
        if action.get("type") == "stop" and isinstance(action.get("answer"), str):
            return action
        return FALLBACK_ACTION.copy()
    except Exception:
        return FALLBACK_ACTION.copy()
