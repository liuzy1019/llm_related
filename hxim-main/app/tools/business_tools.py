"""Offline business functions.

The function names mirror the Hx design document. Mutating actions return a
confirmation requirement instead of changing state directly.
"""

from __future__ import annotations

from typing import Any

from app.data import MOCK_DB


def _missing_order_id(slots: dict[str, Any]) -> dict[str, Any] | None:
    if slots.get("order_id"):
        return None
    return {
        "status": "need_more_info",
        "message": "需要订单号才能继续处理。",
        "missing_slots": ["order_id"],
    }


def execute_business_action(intent: str, slots: dict[str, Any]) -> list[dict[str, Any]]:
    """Execute one or more deterministic business actions for an intent."""
    results: list[dict[str, Any]] = []
    if intent in {"配送", "催单"}:
        results.append(query_delivery_status(slots))
        if intent == "催单":
            results.append(rush_order(slots))
        return results
    if intent in {"退款", "少送错送", "食安", "餐损撒漏", "餐品不符合预期"}:
        if slots.get("requested_action") == "cancel_order":
            return [cancel_order(slots)]
        results.append(query_order(slots))
        if intent == "食安":
            results.append(query_insurance_status(slots))
        results.append(submit_refund(slots))
        return results
    if intent in {"修改订单", "备注"}:
        return [modify_order(slots)]
    return [query_order(slots)]


def query_order(slots: dict[str, Any]) -> dict[str, Any]:
    missing = _missing_order_id(slots)
    if missing:
        return {"function": "query_order", **missing}
    order = MOCK_DB.get_order(str(slots["order_id"]))
    if not order:
        return {
            "function": "query_order",
            "status": "not_found",
            "order_id": slots["order_id"],
            "message": f"没有查到订单 {slots['order_id']}，请确认订单号是否正确。",
        }
    return {
        "function": "query_order",
        "status": "ok",
        "order_id": order["order_id"],
        "order": order,
        "message": (
            f"订单 {order['order_id']} 来自{order['merchant']}，"
            f"包含{'、'.join(order['items'])}，当前状态为 {order['status']}。"
        ),
    }


def query_delivery_status(slots: dict[str, Any]) -> dict[str, Any]:
    missing = _missing_order_id(slots)
    if missing:
        return {"function": "query_delivery_status", **missing}
    order = MOCK_DB.get_order(str(slots["order_id"]))
    if not order:
        return {
            "function": "query_delivery_status",
            "status": "not_found",
            "order_id": slots["order_id"],
            "message": f"没有查到订单 {slots['order_id']}，暂时无法查询配送。",
        }
    delivery = order.get("delivery")
    if not delivery:
        return {
            "function": "query_delivery_status",
            "status": "not_started",
            "order_id": order["order_id"],
            "message": f"订单 {order['order_id']} 当前为 {order['status']}，还没有进入配送。",
        }
    return {
        "function": "query_delivery_status",
        "status": "ok",
        "order_id": order["order_id"],
        "eta_minutes": delivery["eta_minutes"],
        "delivery": delivery,
        "message": (
            f"{delivery['last_event']}；骑手{delivery['courier_name']}距食堂约"
            f" {delivery['distance_km']} 公里，预计 {delivery['eta_minutes']} 分钟送达。"
        ),
    }


def query_insurance_status(slots: dict[str, Any]) -> dict[str, Any]:
    missing = _missing_order_id(slots)
    if missing:
        return {"function": "query_insurance_status", **missing}
    order = MOCK_DB.get_order(str(slots["order_id"]))
    if not order:
        return {
            "function": "query_insurance_status",
            "status": "not_found",
            "order_id": slots["order_id"],
            "message": f"没有查到订单 {slots['order_id']}，暂时无法查询食品安全险。",
        }
    if not order["insurance_enabled"]:
        return {
            "function": "query_insurance_status",
            "status": "not_enabled",
            "message": "该订单未开启食品安全险，但仍可按售后流程提交人工核验。",
        }
    return {
        "function": "query_insurance_status",
        "status": "ok",
        "message": "该订单支持食品安全险，人工客服会继续核验证据材料。",
    }


def rush_order(slots: dict[str, Any]) -> dict[str, Any]:
    missing = _missing_order_id(slots)
    if missing:
        return {"function": "rush_order", **missing}
    order = MOCK_DB.mark_rushed(str(slots["order_id"]))
    if not order:
        return {
            "function": "rush_order",
            "status": "not_found",
            "order_id": slots["order_id"],
            "message": f"没有查到订单 {slots['order_id']}，暂时无法催单。",
        }
    return {
        "function": "rush_order",
        "status": "ok",
        "order_id": order["order_id"],
        "message": f"已向{order['merchant']}和骑手发送催单提醒。",
    }


def cancel_order(slots: dict[str, Any]) -> dict[str, Any]:
    missing = _missing_order_id(slots)
    if missing:
        return {"function": "cancel_order", **missing}
    order = MOCK_DB.get_order(str(slots["order_id"]))
    if not order:
        return {
            "function": "cancel_order",
            "status": "not_found",
            "order_id": slots["order_id"],
            "message": f"没有查到订单 {slots['order_id']}，暂时无法取消。",
        }
    if not order["cancelable"]:
        return {
            "function": "cancel_order",
            "status": "blocked",
            "order_id": order["order_id"],
            "message": f"订单 {order['order_id']} 当前状态为 {order['status']}，不能直接取消，可改走售后退款。",
        }
    return {
        "function": "cancel_order",
        "status": "needs_confirmation",
        "requires_confirmation": True,
        "order_id": order["order_id"],
        "confirmation_prompt": f"确认取消订单 {order['order_id']} 吗？",
        "message": f"取消订单 {order['order_id']} 属于变更操作，需要用户二次确认。",
    }


def submit_refund(slots: dict[str, Any]) -> dict[str, Any]:
    missing = _missing_order_id(slots)
    if missing:
        return {"function": "submit_refund", **missing}
    order = MOCK_DB.get_order(str(slots["order_id"]))
    if not order:
        return {
            "function": "submit_refund",
            "status": "not_found",
            "order_id": slots["order_id"],
            "message": f"没有查到订单 {slots['order_id']}，暂时无法提交退款。",
        }
    if not order["refund_eligible"]:
        return {
            "function": "submit_refund",
            "status": "blocked",
            "order_id": order["order_id"],
            "message": f"订单 {order['order_id']} 当前不满足自动退款条件，建议转人工处理。",
        }
    return {
        "function": "submit_refund",
        "status": "needs_confirmation",
        "requires_confirmation": True,
        "order_id": order["order_id"],
        "confirmation_prompt": f"确认提交订单 {order['order_id']} 的退款申请吗？",
        "message": (
            f"订单 {order['order_id']} 金额 {order['amount_yuan']} 元，"
            "退款申请会影响订单状态，需要用户确认后提交售后工单。"
        ),
    }


def modify_order(slots: dict[str, Any]) -> dict[str, Any]:
    missing = _missing_order_id(slots)
    if missing:
        return {"function": "modify_order", **missing}
    order = MOCK_DB.get_order(str(slots["order_id"]))
    if not order:
        return {
            "function": "modify_order",
            "status": "not_found",
            "order_id": slots["order_id"],
            "message": f"没有查到订单 {slots['order_id']}，暂时无法修改。",
        }
    return {
        "function": "modify_order",
        "status": "needs_confirmation",
        "requires_confirmation": True,
        "order_id": order["order_id"],
        "confirmation_prompt": f"确认修改订单 {order['order_id']} 吗？",
        "message": f"订单 {order['order_id']} 修改前需要用户确认变更内容。",
    }


def submit_complaint(slots: dict[str, Any]) -> dict[str, Any]:
    return {
        "function": "submit_complaint",
        "status": "needs_confirmation",
        "requires_confirmation": True,
        "message": "投诉工单需要用户确认诉求和联系方式后提交。",
    }


def commit_confirmed_mutation(mutation: dict[str, Any]) -> dict[str, Any]:
    """Execute a previously confirmed mutating function in the mock database."""
    function = mutation.get("function")
    order_id = mutation.get("order_id") or (mutation.get("slots") or {}).get("order_id")
    if function == "cancel_order":
        order = MOCK_DB.cancel_order(str(order_id))
        if not order:
            return {
                "function": function,
                "status": "failed",
                "order_id": order_id,
                "message": f"订单 {order_id} 无法取消，请确认订单状态。",
            }
        return {
            "function": function,
            "status": "ok",
            "order_id": order["order_id"],
            "order": order,
            "message": f"已为你取消订单 {order['order_id']}，订单状态已更新为 canceled。",
        }
    if function == "submit_refund":
        ticket = MOCK_DB.submit_refund(str(order_id), mutation.get("intent", "退款"))
        if not ticket:
            return {
                "function": function,
                "status": "failed",
                "order_id": order_id,
                "message": f"订单 {order_id} 暂时无法提交退款申请。",
            }
        return {
            "function": function,
            "status": "ok",
            "order_id": order_id,
            "ticket": ticket,
            "message": f"已提交退款申请，工单号 {ticket['ticket_id']}。",
        }
    if function == "modify_order":
        order = MOCK_DB.record_order_event(str(order_id), "用户已确认修改订单，等待人工核验变更内容")
        return {
            "function": function,
            "status": "ok" if order else "failed",
            "order_id": order_id,
            "order": order,
            "message": (
                f"已记录订单 {order_id} 的修改确认，稍后按变更内容处理。"
                if order
                else f"订单 {order_id} 暂时无法修改。"
            ),
        }
    return {
        "function": function or "unknown_mutation",
        "status": "failed",
        "order_id": order_id,
        "message": "当前确认操作暂不支持执行。",
    }
