"""Strict, non-fabricating evidence checks for Issue #292 CLI JSONL runs."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _agent_message(event: dict[str, Any]) -> str | None:
    if event.get("type") != "item.completed":
        return None
    item = event.get("item")
    if isinstance(item, dict) and item.get("type") == "agent_message":
        text = item.get("text")
        if isinstance(text, str):
            return text
    return None


def inspect(raw_events: bytes, final_bytes: bytes | None) -> dict[str, Any]:
    """Return evidence metadata without retaining or synthesizing event content."""
    errors: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    lines = raw_events.splitlines()
    for number, raw_line in enumerate(lines, start=1):
        if not raw_line:
            errors.append({"line": number, "error_class": "blank_jsonl_line"})
            continue
        try:
            decoded = raw_line.decode("utf-8")
        except UnicodeDecodeError:
            errors.append({"line": number, "error_class": "invalid_utf8"})
            continue
        try:
            value = json.loads(decoded)
        except json.JSONDecodeError:
            errors.append({"line": number, "error_class": "malformed_json"})
            continue
        if not isinstance(value, dict):
            errors.append({"line": number, "error_class": "non_object_json"})
            continue
        events.append(value)

    messages = [text for event in events if (text := _agent_message(event)) is not None]
    terminals = [event for event in events if event.get("type") in {"turn.completed", "turn.failed", "error"}]
    completed = [event for event in terminals if event.get("type") == "turn.completed"]
    failed = [event for event in terminals if event.get("type") in {"turn.failed", "error"}]
    turn_status = "completed"
    if not terminals:
        turn_status = "missing"
        errors.append({"line": None, "error_class": "missing_terminal_event"})
    if failed:
        turn_status = "failed"
        errors.append({"line": None, "error_class": "terminal_failure"})
    if not completed:
        turn_status = "missing" if not failed else "failed"
        errors.append({"line": None, "error_class": "missing_turn_completed"})

    final_text: str | None = None
    if final_bytes is None:
        errors.append({"line": None, "error_class": "missing_final_output"})
    else:
        if not final_bytes:
            errors.append({"line": None, "error_class": "empty_final_output"})
        try:
            final_text = final_bytes.decode("utf-8")
        except UnicodeDecodeError:
            errors.append({"line": None, "error_class": "final_invalid_utf8"})
    if final_text is not None:
        if not messages:
            errors.append({"line": None, "error_class": "missing_agent_message"})
        elif final_text.rstrip("\r\n") != messages[-1].rstrip("\r\n"):
            errors.append({"line": None, "error_class": "final_message_mismatch"})

    usage = completed[-1].get("usage") if completed else None
    return {
        "stream_integrity": "valid" if not errors else "invalid",
        "turn_status": turn_status,
        "tool_coverage": "not_assessed",
        "errors": errors,
        "raw_event_sha256": _sha256(raw_events),
        "raw_event_bytes": len(raw_events),
        "raw_event_line_count": len(lines),
        "final_sha256": _sha256(final_bytes) if final_bytes is not None else None,
        "final_bytes": len(final_bytes) if final_bytes is not None else None,
        "terminal_event_types": [event.get("type") for event in terminals],
        "agent_message_count": len(messages),
        "command_event_count": sum(
            event.get("type") == "item.completed"
            and isinstance(event.get("item"), dict)
            and event["item"].get("type") == "command_execution"
            for event in events
        ),
        "usage": usage,
    }
