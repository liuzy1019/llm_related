"""ReAct Agent：手动构建版

对应文章 3.1 节"手动构建 ReAct（理解底层原理）"。
增加生产实践：iteration_count 防无限循环。
"""

from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.llm import get_llm
from app.state.schemas import ReActState
from app.tools import DEFAULT_TOOLS

MAX_ITERATIONS = 10


def _build_nodes():
    llm = get_llm()
    llm_with_tools = llm.bind_tools(DEFAULT_TOOLS)

    def agent_node(state: ReActState) -> Dict[str, Any]:
        # 防无限循环
        if state.get("iteration_count", 0) >= MAX_ITERATIONS:
            return {
                "messages": [AIMessage(content="已达最大迭代次数，请简化问题后重试。")],
                "iteration_count": state.get("iteration_count", 0),
            }
        response = llm_with_tools.invoke(state["messages"])
        return {
            "messages": [response],
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    def route_after_agent(state: ReActState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    return agent_node, route_after_agent


def build_react_graph():
    """构建并编译 ReAct 图。"""
    agent_node, route_after_agent = _build_nodes()

    builder = StateGraph(ReActState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(DEFAULT_TOOLS))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_after_agent, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")  # 工具执行后回到 agent，形成循环

    return builder
