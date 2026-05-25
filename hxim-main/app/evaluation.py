"""Adapters for IM_autoeval and IM_board compatible records."""

from __future__ import annotations

from typing import Any

from app.data import MOCK_DB
from app.domain.im_standards import (
    ANNOTATION_FIELDS,
    AUTOEVAL_INPUT_FIELDS,
    AUTOEVAL_OUTPUT_FIELDS,
    BOARD_FIELDS,
    format_board_intent,
    now_shanghai_like,
    stable_hive_id,
    to_json_text,
)
from app.settings import settings
from app.session_store import SessionSnapshot


def build_evaluation_payloads(
    result: dict[str, Any],
    session: SessionSnapshot,
    user_id: str,
) -> dict[str, dict[str, Any]]:
    """Build the two external data shapes used by the imported IM systems."""
    _, date, timestamp, epoch_ms = now_shanghai_like()
    intent = result.get("intent", "澄清")
    evaluation_id = stable_hive_id(session.session_id, epoch_ms)
    order = _primary_order(result)
    wm_poi_id = _wm_poi_id(order)
    session_data_string = to_json_text(session.history)
    problem_solved = _problem_solved(result)
    decision_data = _decision_data(result)
    model_out = _model_out(result, problem_solved, decision_data)

    autoeval = {
        "querys": result.get("query", ""),
        "historys": session_data_string,
        "wmPoiId": wm_poi_id,
        "messageType": "text",
        "orderinfo": to_json_text(order) if order else "",
        "imagemessage": "",
        "intent": intent,
        "response": result.get("reply", ""),
        "botOutput": result.get("reply", ""),
        "ModelOut": model_out,
        "decisionData": decision_data,
        "problemSolved": problem_solved,
        "toHuman": bool(result.get("escalate", False)),
        "__sys_aibox_llm_result_code": "SUCCESS",
        "任务状态": "已完成",
    }

    board_record = {
        "id": evaluation_id,
        "session_id": session.session_id,
        "im_session_id": session.session_id,
        "date": date,
        "wm_poi_id": wm_poi_id,
        "user_id": user_id,
        "intent": format_board_intent(intent),
        "is_accurate": None,
        "inaccuracy_reason": "",
        "is_resolved": 1 if problem_solved == "已解决" else 0,
        "create_time": timestamp,
        "update_time": timestamp,
        "session_data_string": session_data_string,
        "evaluation_workflow_version": 1,
        "is_resolved_label": None,
        "is_accurate_label": None,
        "dt": date,
    }
    annotation_record = {
        **board_record,
        "hive_id": evaluation_id,
    }
    annotation_record.pop("id", None)

    return {
        "autoeval": _ordered(autoeval, AUTOEVAL_INPUT_FIELDS + AUTOEVAL_OUTPUT_FIELDS),
        "board_record": _ordered(board_record, BOARD_FIELDS),
        "annotation_record": _ordered(annotation_record, ANNOTATION_FIELDS),
        "evaluation_meta": {
            "generated_at": timestamp,
            "generated_at_ms": epoch_ms,
            "standard": "IM_autoeval + IM_board",
        },
    }


def _ordered(data: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: data.get(field) for field in fields}


def _primary_order(result: dict[str, Any]) -> dict[str, Any] | None:
    for function_result in result.get("function_results", []):
        order = function_result.get("order")
        if order:
            return order
    order_id = (result.get("slots") or {}).get("order_id")
    if order_id:
        return MOCK_DB.get_order(str(order_id))
    return None


def _wm_poi_id(order: dict[str, Any] | None) -> str:
    if order and order.get("merchant"):
        return {
            "浣熊食堂一号窗口": "100001",
            "轻食沙拉档口": "100002",
            "面点窗口": "100003",
        }.get(str(order["merchant"]), "100000")
    return getattr(settings, "default_wm_poi_id", "100000")


def _problem_solved(result: dict[str, Any]) -> str:
    if result.get("escalate"):
        return "未解决"
    if _has_missing_slots(result) or _needs_confirmation(result):
        return "未解决"
    if result.get("intent") in {"闲聊"}:
        return "已解决"
    if any(item.get("status") in {"not_found", "blocked"} for item in result.get("function_results", [])):
        return "未解决"
    return "已解决"


def _has_missing_slots(result: dict[str, Any]) -> bool:
    return any(item.get("missing_slots") for item in result.get("function_results", []))


def _needs_confirmation(result: dict[str, Any]) -> bool:
    return any(item.get("requires_confirmation") for item in result.get("function_results", []))


def _decision_data(result: dict[str, Any]) -> str:
    decisions: list[dict[str, str]] = []
    reply = result.get("reply")
    if reply:
        decisions.append({"code": "send_text_message", "data": to_json_text(reply)})
    if result.get("escalate"):
        decisions.append({"code": "transfer_to_human", "data": to_json_text("转人工")})
    if any(item.get("function") == "rush_order" for item in result.get("function_results", [])):
        decisions.append({"code": "notify_store_manager", "data": to_json_text({"intent": "催单"})})
    return to_json_text(decisions)


def _model_out(result: dict[str, Any], problem_solved: str, decision_data: str) -> dict[str, Any]:
    return {
        "hxIntentDO": {
            "intent": result.get("intent", "澄清"),
            "confidence": result.get("confidence", 0),
            "problemSolved": problem_solved,
            "reason": _reason(result),
            "clarification": _clarification(result),
        },
        "intent": result.get("intent", "澄清"),
        "response": result.get("reply", ""),
        "botMemory": to_json_text(result.get("memory_updates", {})),
        "toHuman": bool(result.get("escalate", False)),
        "conversationEnd": problem_solved == "已解决",
        "replyToUser": True,
        "decisionData": decision_data,
    }


def _reason(result: dict[str, Any]) -> str:
    intent = result.get("intent", "澄清")
    route = result.get("route", "HYBRID")
    order_id = (result.get("slots") or {}).get("order_id")
    if order_id:
        return f"命中标准意图【{intent}】，已匹配订单 {order_id}，路由 {route}。"
    return f"命中标准意图【{intent}】，当前未匹配到订单，路由 {route}。"


def _clarification(result: dict[str, Any]) -> str:
    missing: list[str] = []
    for item in result.get("function_results", []):
        missing.extend(item.get("missing_slots") or [])
    return "请补充：" + "、".join(missing) if missing else ""
