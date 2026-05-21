"""Multi-Agent（Supervisor 模式）

文章在 3.4 节提到子图与多 Agent 协作。这里给一个最常用范式：
- supervisor 节点：决定下一步去哪个 worker（researcher / calculator / editor / FINISH）
- researcher 节点：负责调用搜索类工具
- calculator 节点：负责调用计算工具
- editor 节点：负责向当前文件追加文本
- 多方共享 messages，supervisor 通过最后一条 AIMessage 决定路由
"""

from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent

from app.llm import get_llm
from app.state.schemas import MultiAgentState
from app.tools.code_tools import calculate
from app.tools.file_tools import type_in_current_file
from app.tools.search_tools import search_weather, search_web

MAX_ITERATIONS = 6
WORKERS = ("researcher", "calculator", "editor")


def _requested_workers(text: str) -> list[str]:
    """按固定顺序列出用户问题需要哪些 worker。"""
    t = text or ""
    workers: list[str] = []
    if any(kw in t for kw in ("天气", "搜索", "查一下", "weather", "search")):
        workers.append("researcher")
    if any(c in t for c in "0123456789") and any(c in t for c in "+-*/x×"):
        workers.append("calculator")
    if "当前文件" in t and any(kw in t for kw in ("键入", "写入", "追加", "输入")):
        workers.append("editor")
    return workers


def build_multi_agent_graph():
    """构建 Supervisor 多 Agent 图。

    supervisor 只负责调度；researcher/calculator 是两个可替换的 worker。
    """
    llm = get_llm()
    # 每个 worker 都是一个 prebuilt ReAct agent，只是能使用的工具不同。
    researcher = create_react_agent(llm, tools=[search_weather, search_web])
    calculator = create_react_agent(llm, tools=[calculate])
    editor = create_react_agent(llm, tools=[type_in_current_file])

    def supervisor_node(state: MultiAgentState) -> Dict[str, Any]:
        """调度节点：根据原始问题和已完成工具结果，决定下一个 worker。"""
        # 防无限循环：多 Agent 互相来回路由时必须有硬上限。
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
        # ToolMessage 的 name 能告诉 supervisor 某类任务是否已经被 worker 完成。
        already_done = {
            "researcher": ("天气" in text or "search_weather" in text)
            and any(
                getattr(m, "name", "") in {"search_weather", "search_web"}
                for m in state["messages"]
            ),
            "calculator": any(
                getattr(m, "name", "") == "calculate" for m in state["messages"]
            ),
            "editor": any(
                getattr(m, "name", "") == "type_in_current_file" for m in state["messages"]
            ),
        }
        requested = _requested_workers(last_human)
        next_step = next((worker for worker in requested if not already_done[worker]), "FINISH")

        return {
            "next": next_step,
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    def make_worker_node(agent, name: str):
        def _node(state: MultiAgentState) -> Dict[str, Any]:
            """worker 节点：调用子 agent，并把它新产生的消息追加回共享 state。"""
            result = agent.invoke({"messages": state["messages"]})
            # 追加 worker 新产生的消息，保留 ToolMessage 供 supervisor 判断进度。
            new_messages = result["messages"][len(state["messages"]) :]
            final = new_messages[-1]
            if not isinstance(final, AIMessage):
                final = AIMessage(content=str(final.content))
                new_messages[-1] = final
            final.name = name
            return {"messages": new_messages}

        return _node

    def route_supervisor(state: MultiAgentState) -> str:
        """条件边：把 supervisor 写入的 next 映射成下一跳节点。"""
        nxt = state.get("next") or "FINISH"
        return nxt if nxt in WORKERS else END

    builder = StateGraph(MultiAgentState)
    # supervisor 是中心调度器；worker 执行完成后都会回到 supervisor。
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("researcher", make_worker_node(researcher, "researcher"))
    builder.add_node("calculator", make_worker_node(calculator, "calculator"))
    builder.add_node("editor", make_worker_node(editor, "editor"))

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {"researcher": "researcher", "calculator": "calculator", "editor": "editor", END: END},
    )
    builder.add_edge("researcher", "supervisor")
    builder.add_edge("calculator", "supervisor")
    builder.add_edge("editor", "supervisor")
    return builder
