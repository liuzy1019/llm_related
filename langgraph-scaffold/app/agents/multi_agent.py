"""Multi-Agent（Supervisor 模式）

文章在 3.4 节提到子图与多 Agent 协作。这里给一个最常用范式：
- supervisor 节点：决定下一步去哪个 worker（researcher / calculator / FINISH）
- researcher 节点：负责调用搜索类工具
- calculator 节点：负责调用计算工具
- 三方共享 messages，supervisor 通过最后一条 AIMessage 决定路由
"""

from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent

from app.llm import get_llm
from app.state.schemas import MultiAgentState
from app.tools.code_tools import calculate
from app.tools.search_tools import search_weather, search_web

MAX_ITERATIONS = 6
WORKERS = ("researcher", "calculator")


def _heuristic_route(text: str) -> str:
    """极简启发式路由：用于在没有真实 LLM 时也能演示多 Agent。"""
    t = text or ""
    has_calc = any(c in t for c in "0123456789") and any(c in t for c in "+-*/x×")
    has_search = any(kw in t for kw in ("天气", "搜索", "查一下", "weather", "search"))
    if has_search:
        return "researcher"
    if has_calc:
        return "calculator"
    return "FINISH"


def build_multi_agent_graph():
    llm = get_llm()
    researcher = create_react_agent(llm, tools=[search_weather, search_web])
    calculator = create_react_agent(llm, tools=[calculate])

    def supervisor_node(state: MultiAgentState) -> Dict[str, Any]:
        # 防无限循环
        if state.get("iteration_count", 0) >= MAX_ITERATIONS:
            return {
                "next": "FINISH",
                "iteration_count": state.get("iteration_count", 0),
            }

        # 取最近一条用户/工具消息内容供启发式判断
        last_human = next(
            (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            "",
        )
        # 先看是否已有 worker 完成了对应任务，若有则可终止
        text = "\n".join(getattr(m, "content", "") or "" for m in state["messages"])

        # 简单策略：每轮根据原始 query 选一个尚未完成的子任务，否则 FINISH
        next_step = _heuristic_route(last_human)
        already_done = {
            "researcher": ("天气" in text or "search_weather" in text)
            and any(
                getattr(m, "name", "") in {"search_weather", "search_web"}
                for m in state["messages"]
            ),
            "calculator": any(
                getattr(m, "name", "") == "calculate" for m in state["messages"]
            ),
        }
        if next_step in WORKERS and already_done.get(next_step):
            # 已完成该方向 → 尝试切换到另一个；都完成则 FINISH
            other = "calculator" if next_step == "researcher" else "researcher"
            need_other = (
                ("天气" in last_human or "search" in last_human.lower())
                if other == "researcher"
                else any(c in last_human for c in "0123456789")
            )
            next_step = other if need_other and not already_done[other] else "FINISH"

        return {
            "next": next_step,
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    def make_worker_node(agent, name: str):
        def _node(state: MultiAgentState) -> Dict[str, Any]:
            result = agent.invoke({"messages": state["messages"]})
            # 仅追加 worker 的最后一条 AIMessage，避免噪声爆炸
            final = result["messages"][-1]
            if not isinstance(final, AIMessage):
                final = AIMessage(content=str(final.content))
            final.name = name
            return {"messages": [final]}

        return _node

    def route_supervisor(state: MultiAgentState) -> str:
        nxt = state.get("next") or "FINISH"
        return nxt if nxt in WORKERS else END

    builder = StateGraph(MultiAgentState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("researcher", make_worker_node(researcher, "researcher"))
    builder.add_node("calculator", make_worker_node(calculator, "calculator"))

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {"researcher": "researcher", "calculator": "calculator", END: END},
    )
    builder.add_edge("researcher", "supervisor")
    builder.add_edge("calculator", "supervisor")
    return builder
