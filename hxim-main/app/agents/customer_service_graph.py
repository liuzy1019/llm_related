"""Hx canteen customer service LangGraph.

The graph implements the recommended Hybrid Coordinator path from the design:

Router -> Knowledge / Action / Hybrid / Chitchat / Escalate -> Generator
       -> Memory

Each node returns partial state updates. The graph stays deterministic in mock
mode, making it suitable for CI and for replacing one node at a time with LLM,
RAG or real order-system integrations.
"""

from __future__ import annotations

import re
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.data import MOCK_DB
from app.domain.catalog import search_knowledge
from app.domain.heuristics import (
    decide_route,
    detect_emotion,
    detect_intent,
    detect_stage,
    extract_slots,
    normalize_text,
    should_escalate,
)
from app.settings import settings
from app.state.schemas import CustomerServiceState
from app.tools.business_tools import execute_business_action


def router_agent(state: CustomerServiceState) -> dict[str, Any]:
    """Router Agent: merge Step 0-5 into a single routing decision."""
    query = state["query"]
    normalized_query = normalize_text(query)
    carried_intent = state.get("carried_intent")
    slots = {**state.get("carried_slots", {}), **extract_slots(normalized_query)}
    if carried_intent:
        intent, confidence = carried_intent, 0.91
    else:
        intent, confidence = detect_intent(normalized_query)
    stage = detect_stage(intent)
    emotion = detect_emotion(normalized_query)
    escalate, escalate_reason = should_escalate(
        normalized_query,
        intent,
        emotion,
        confidence,
    )
    route = decide_route(intent, slots, escalate)
    memory_snapshot = recall_memory(state.get("user_id", settings.default_user_id))

    return {
        "normalized_query": normalized_query,
        "memory_snapshot": memory_snapshot,
        "intent": intent,
        "stage": stage,
        "emotion": emotion,
        "confidence": confidence,
        "escalate": escalate,
        "escalate_reason": escalate_reason,
        "route": route,
        "slots": slots,
        "trace": [
            f"router:{intent}:{route}"
            + (":carried" if carried_intent else ""),
        ],
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


def knowledge_agent(state: CustomerServiceState) -> dict[str, Any]:
    """Knowledge Agent: intent-routed RAG placeholder."""
    results = search_knowledge(
        state.get("intent", "澄清"),
        state.get("normalized_query", state["query"]),
    )
    return {
        "rag_results": results,
        "trace": [f"knowledge:{len(results)}"],
    }


def action_agent(state: CustomerServiceState) -> dict[str, Any]:
    """Action Agent: execute deterministic business functions.

    This is where the Step 8.5 Agent Loop belongs. The offline implementation
    limits itself to at most ``MAX_AGENT_LOOP_ITERATIONS`` function results.
    """
    results = execute_business_action(state.get("intent", "澄清"), state.get("slots", {}))
    limited = results[: settings.max_agent_loop_iterations]
    return {
        "function_results": limited,
        "trace": [f"action:{','.join(r['function'] for r in limited)}"],
    }


def hybrid_agent(state: CustomerServiceState) -> dict[str, Any]:
    """Hybrid Agent: run knowledge retrieval and business functions together."""
    knowledge = search_knowledge(
        state.get("intent", "澄清"),
        state.get("normalized_query", state["query"]),
    )
    function_results = execute_business_action(
        state.get("intent", "澄清"),
        state.get("slots", {}),
    )[: settings.max_agent_loop_iterations]
    return {
        "rag_results": knowledge,
        "function_results": function_results,
        "trace": [
            f"hybrid:knowledge={len(knowledge)}:action={len(function_results)}",
        ],
    }


def generator_agent(state: CustomerServiceState) -> dict[str, Any]:
    """Generator Agent: produce a final customer-facing answer."""
    if state.get("route") == "ESCALATE":
        reason = state.get("escalate_reason") or "manual_review"
        reply = "这个问题我会立即为你转接人工客服处理。"
        if reason == "p0_food_safety":
            reply += "请先保留餐品、包装和照片，人工客服会优先跟进食品安全问题。"
        return {"reply": reply, "trace": ["generator:escalate"]}

    if state.get("route") == "CHITCHAT":
        return {
            "reply": "你好，我是浣熊食堂智能客服。你可以问我订单、配送、退款或菜品问题。",
            "trace": ["generator:chitchat"],
        }

    missing = _first_missing_slots(state.get("function_results", []))
    if missing:
        return {
            "reply": "我可以继续处理，请先补充：" + "、".join(missing),
            "trace": ["generator:ask_user"],
        }

    confirmations = [
        result["message"]
        for result in state.get("function_results", [])
        if result.get("requires_confirmation")
    ]
    if confirmations:
        return {
            "reply": "需要你确认后我再提交：" + "；".join(confirmations),
            "trace": ["generator:needs_confirmation"],
        }

    parts: list[str] = []
    for result in state.get("function_results", []):
        if result.get("message"):
            parts.append(str(result["message"]))
    if state.get("rag_results"):
        knowledge = state["rag_results"][0]
        parts.append(f"参考规则：{knowledge['content']}")

    if not parts:
        parts.append("我已收到你的问题，会按食堂客服流程继续处理。")

    return {
        "reply": " ".join(parts),
        "trace": ["generator:reply"],
    }


def memory_agent(state: CustomerServiceState) -> dict[str, Any]:
    """Memory Agent: extract durable user facts from the turn."""
    updates = extract_memory_updates(state.get("normalized_query", state["query"]))
    return {
        "memory_updates": updates,
        "trace": [f"memory:{','.join(updates) if updates else 'none'}"],
    }


def route_from_router(state: CustomerServiceState) -> str:
    """Map Router route labels to graph nodes."""
    route = state.get("route", "HYBRID")
    if route in {"ESCALATE", "CHITCHAT"}:
        return "generator"
    if route == "KNOWLEDGE":
        return "knowledge"
    if route == "ACTION":
        return "action"
    return "hybrid"


def build_customer_service_graph() -> StateGraph:
    """Build the Hx customer service agent graph."""
    builder = StateGraph(CustomerServiceState)
    builder.add_node("router", router_agent)
    builder.add_node("knowledge", knowledge_agent)
    builder.add_node("action", action_agent)
    builder.add_node("hybrid", hybrid_agent)
    builder.add_node("generator", generator_agent)
    builder.add_node("memory", memory_agent)

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router",
        route_from_router,
        {
            "knowledge": "knowledge",
            "action": "action",
            "hybrid": "hybrid",
            "generator": "generator",
        },
    )
    builder.add_edge("knowledge", "generator")
    builder.add_edge("action", "generator")
    builder.add_edge("hybrid", "generator")
    builder.add_edge("generator", "memory")
    builder.add_edge("memory", END)
    return builder


def recall_memory(user_id: str) -> dict[str, Any]:
    """Return a small memory snapshot; replace with ChromaDB in production."""
    user = MOCK_DB.get_user(user_id) or {}
    return {
        "user_id": user_id,
        "profile": user,
        "session_summary": "",
    }


def extract_memory_updates(text: str) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if "不吃辣" in text or "少辣" in text:
        updates["spicy_preference"] = "less_spicy"
    allergy_match = re.search(r"(花生|香菜|海鲜|牛奶).*过敏", text)
    if allergy_match:
        updates["allergy"] = allergy_match.group(1)
    return updates


def _first_missing_slots(results: list[dict[str, Any]]) -> list[str]:
    for result in results:
        missing = result.get("missing_slots")
        if missing:
            return list(missing)
    return []
