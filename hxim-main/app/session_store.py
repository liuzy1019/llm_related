"""In-memory session store for demo multi-turn conversations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SessionSnapshot:
    session_id: str
    pending_intent: str | None = None
    pending_slots: dict[str, Any] = field(default_factory=dict)
    missing_slots: list[str] = field(default_factory=list)
    pending_mutation: dict[str, Any] | None = None
    last_reply: str = ""
    turn_count: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)


class SessionStore:
    """Tiny process-local store used by API and interactive CLI demos."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionSnapshot] = {}

    def get(self, session_id: str) -> SessionSnapshot:
        session = self._sessions.get(session_id)
        if session is None:
            session = SessionSnapshot(session_id=session_id)
            self._sessions[session_id] = session
        return deepcopy(session)

    def save_from_result(self, session_id: str, result: dict[str, Any]) -> SessionSnapshot:
        current = self._sessions.get(session_id) or SessionSnapshot(session_id=session_id)
        _append_turn(current, result)
        missing_slots = _first_missing_slots(result.get("function_results", []))
        if missing_slots:
            current.pending_intent = result.get("intent")
            current.pending_slots = dict(result.get("slots") or {})
            current.missing_slots = missing_slots
            current.pending_mutation = None
        elif mutation := _first_pending_mutation(result):
            current.pending_intent = None
            current.pending_slots = {}
            current.missing_slots = []
            current.pending_mutation = mutation
        elif result.get("route") in {"KNOWLEDGE", "CHITCHAT", "ESCALATE"}:
            current.pending_intent = None
            current.pending_slots = {}
            current.missing_slots = []
            current.pending_mutation = None
        else:
            current.pending_intent = None
            current.pending_slots = {}
            current.missing_slots = []
            current.pending_mutation = None

        current.last_reply = result.get("reply", "")
        current.turn_count += 1
        self._sessions[session_id] = current
        return deepcopy(current)

    def reset(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


def _first_missing_slots(results: list[dict[str, Any]]) -> list[str]:
    for result in results:
        missing = result.get("missing_slots")
        if missing:
            return list(missing)
    return []


def _first_pending_mutation(result: dict[str, Any]) -> dict[str, Any] | None:
    for item in result.get("function_results", []):
        if item.get("requires_confirmation"):
            return {
                "intent": result.get("intent"),
                "function": item.get("function"),
                "order_id": item.get("order_id"),
                "slots": dict(result.get("slots") or {}),
                "message": item.get("message", ""),
                "confirmation_prompt": item.get("confirmation_prompt", ""),
            }
    return None


def _append_turn(current: SessionSnapshot, result: dict[str, Any]) -> None:
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    intent = result.get("intent", "澄清")
    to_human_agent = 1 if result.get("escalate") else 0
    problem_solved = _turn_problem_solved(result)
    current.history.append(
        {
            "role": "user",
            "content": result.get("query", ""),
            "message": result.get("query", ""),
            "timestamp": timestamp,
            "intent": intent,
            "intent_agent": {
                "intent": intent,
                "confidence": result.get("confidence", 0),
                "problemSolved": problem_solved,
            },
            "to_human_agent": to_human_agent,
            "im_session_id": current.session_id,
        }
    )
    current.history.append(
        {
            "role": "poi<人工>" if to_human_agent else "poi<机器人>",
            "content": result.get("reply", ""),
            "message": result.get("reply", ""),
            "timestamp": timestamp,
            "reply_to_user": 1,
            "to_human_agent": to_human_agent,
            "im_session_id": current.session_id,
        }
    )


def _turn_problem_solved(result: dict[str, Any]) -> str:
    if result.get("escalate"):
        return "未解决"
    if _first_missing_slots(result.get("function_results", [])):
        return "未解决"
    if any(item.get("requires_confirmation") for item in result.get("function_results", [])):
        return "未解决"
    if any(item.get("status") in {"not_found", "blocked"} for item in result.get("function_results", [])):
        return "未解决"
    return "已解决"


SESSION_STORE = SessionStore()
