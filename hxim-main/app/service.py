"""Application service layer for chat orchestration."""

from __future__ import annotations

from typing import Any

from app.agents import build_customer_service_graph
from app.domain.heuristics import detect_intent, extract_slots, normalize_text
from app.evaluation import build_evaluation_payloads
from app.session_store import SESSION_STORE, SessionStore
from app.settings import settings
from app.tools.business_tools import commit_confirmed_mutation


class ChatService:
    """Wrap the graph with session-aware pre/post processing."""

    def __init__(self, session_store: SessionStore = SESSION_STORE) -> None:
        self.graph = build_customer_service_graph().compile()
        self.session_store = session_store

    def chat(
        self,
        query: str,
        session_id: str = settings.default_session_id,
        user_id: str = settings.default_user_id,
    ) -> dict[str, Any]:
        session = self.session_store.get(session_id)
        normalized_query = normalize_text(query)
        if session.pending_mutation and (decision := _confirmation_decision(normalized_query)):
            result = _handle_pending_mutation(
                query=query,
                session_id=session_id,
                user_id=user_id,
                mutation=session.pending_mutation,
                decision=decision,
            )
            saved = self.session_store.save_from_result(session_id, result)
            result["session"] = _session_payload(saved)
            result.update(build_evaluation_payloads(result, saved, user_id))
            return result

        current_slots = extract_slots(normalized_query)
        current_intent, current_confidence = detect_intent(normalized_query)
        carried_intent = None
        carried_slots: dict[str, Any] = {}

        if (
            session.pending_intent
            and _fills_missing_slots(current_slots, session.missing_slots)
            and not _should_interrupt_pending(current_intent, current_confidence)
        ):
            carried_intent = session.pending_intent
            carried_slots = {**session.pending_slots, **current_slots}

        result = self.graph.invoke(
            {
                "query": query,
                "session_id": session_id,
                "user_id": user_id,
                "iteration_count": 0,
                "carried_intent": carried_intent,
                "carried_slots": carried_slots,
            },
            config={"configurable": {"thread_id": session_id}},
        )
        saved = self.session_store.save_from_result(session_id, result)
        result["session"] = _session_payload(saved)
        result.update(build_evaluation_payloads(result, saved, user_id))
        return result

    def reset(self, session_id: str) -> dict[str, str]:
        self.session_store.reset(session_id)
        return {"status": "ok", "session_id": session_id}


def _fills_missing_slots(slots: dict[str, Any], missing_slots: list[str]) -> bool:
    return bool(missing_slots) and all(slot in slots for slot in missing_slots)


def _should_interrupt_pending(intent: str, confidence: float) -> bool:
    if intent in {"食安", "转人工"}:
        return True
    return confidence >= 0.9 and intent not in {"澄清", "闲聊"}


def _confirmation_decision(text: str) -> str:
    stripped = text.strip()
    if stripped in {"确认", "确定", "是", "可以", "同意", "提交", "继续", "好的", "好"}:
        return "confirm"
    if stripped in {"取消", "不用了", "不要", "否", "不是", "算了", "先不"}:
        return "cancel"
    return ""


def _handle_pending_mutation(
    query: str,
    session_id: str,
    user_id: str,
    mutation: dict[str, Any],
    decision: str,
) -> dict[str, Any]:
    intent = mutation.get("intent") or "澄清"
    slots = dict(mutation.get("slots") or {})
    if decision == "cancel":
        function_result = {
            "function": mutation.get("function", "pending_mutation"),
            "status": "canceled",
            "order_id": mutation.get("order_id"),
            "message": "已取消本次待确认操作，不会继续提交。",
        }
        reply = function_result["message"]
    else:
        function_result = commit_confirmed_mutation(mutation)
        reply = function_result.get("message", "已确认并完成操作。")
    return {
        "query": query,
        "session_id": session_id,
        "user_id": user_id,
        "normalized_query": normalize_text(query),
        "memory_snapshot": {},
        "intent": intent,
        "stage": "after_sale",
        "emotion": "neutral",
        "confidence": 1.0,
        "route": "ACTION",
        "escalate": False,
        "escalate_reason": "",
        "slots": slots,
        "rag_results": [],
        "function_results": [function_result],
        "reply": reply,
        "memory_updates": {},
        "trace": [f"confirm:{decision}:{function_result.get('function')}"],
        "iteration_count": 1,
    }


def _session_payload(saved) -> dict[str, Any]:
    return {
        "session_id": saved.session_id,
        "pending_intent": saved.pending_intent,
        "pending_slots": saved.pending_slots,
        "missing_slots": saved.missing_slots,
        "pending_mutation": saved.pending_mutation,
        "turn_count": saved.turn_count,
        "history": saved.history,
    }


CHAT_SERVICE = ChatService()
