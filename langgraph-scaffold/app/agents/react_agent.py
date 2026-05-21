"""ReAct Agent：手动构建版。

对应文章 3.1 节"手动构建 ReAct（理解底层原理）"。
增加生产实践：iteration_count 防无限循环。

ReAct = Reasoning + Acting，直译就是“推理 + 行动”：
1. Reasoning：LLM 先根据用户问题和历史消息判断下一步要不要调用工具；
2. Acting：如果要调用工具，LLM 在 AIMessage.tool_calls 里声明工具名和参数；
3. Observe：ToolNode 执行工具，并把 ToolMessage 追加到 messages；
4. 再 Reasoning：LLM 看到工具结果后，继续判断是回答用户还是继续调用工具。

这份文件没有使用 LangGraph 的 create_react_agent 快捷函数，而是手动搭图，
目的就是把 ReAct 的循环结构展示出来。
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
    """创建图里要用到的节点函数和路由函数。

    LangGraph 的节点本质上就是普通 Python 函数：
    - 入参是当前 state；
    - 返回值是一个 dict；
    - 返回 dict 会被 LangGraph 合并回 state。
    """
    # 取当前配置下的模型。没有 API Key 时，这里会返回 MockChatLLM。
    llm = get_llm()

    # bind_tools 会告诉模型“你可以调用哪些工具”。
    # 真实 LLM 会根据工具 schema 生成 tool_calls；
    # Mock LLM 则用正则识别城市/算式来模拟 tool_calls。
    llm_with_tools = llm.bind_tools(DEFAULT_TOOLS)

    def agent_node(state: ReActState) -> Dict[str, Any]:
        """LLM 决策节点。

        这个节点对应 ReAct 里的 Reasoning 阶段。

        输入：
            state["messages"]：完整消息历史，包括 HumanMessage、AIMessage、ToolMessage。

        输出：
            {
                "messages": [response],
                "iteration_count": old + 1,
            }

        注意：
            messages 字段在 ReActState 里配置了 add_messages reducer，
            所以这里返回 [response] 不会覆盖历史，而是追加到历史末尾。
        """
        # 生产实践：Agent 循环必须有硬上限。
        # 否则如果模型一直调用工具，图会一直在 agent <-> tools 之间循环。
        if state.get("iteration_count", 0) >= MAX_ITERATIONS:
            return {
                "messages": [AIMessage(content="已达最大迭代次数，请简化问题后重试。")],
                "iteration_count": state.get("iteration_count", 0),
            }

        # 调用绑定了工具的 LLM。
        # 可能出现两种结果：
        # 1. response.tool_calls 非空：表示模型想调用工具；
        # 2. response.tool_calls 为空：表示模型已经可以直接回答用户。
        response = llm_with_tools.invoke(state["messages"])

        # 只返回本节点要更新的字段。
        # LangGraph 会根据 ReActState 的 reducer 把它们合并回全局 state。
        return {
            "messages": [response],
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    def route_after_agent(state: ReActState) -> str:
        """条件边路由函数：决定 agent 后面是执行工具还是结束。

        这个函数不修改 state，只返回下一跳名称。
        返回 "tools"：进入 ToolNode 执行工具；
        返回 END：结束整张图。
        """
        # agent_node 刚刚追加了一条 AIMessage，所以最后一条消息就是模型输出。
        last = state["messages"][-1]

        # LangChain 的 AIMessage 如果包含工具调用，会有 tool_calls 字段。
        # ToolNode 正是依靠这个字段知道要执行哪个工具、传入什么参数。
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    return agent_node, route_after_agent


def build_react_graph():
    """构建 ReAct 图。

    拓扑结构：
        START -> agent -> tools -> agent -> ... -> END

    读图方式：
    - START / END 是 LangGraph 的特殊标记，不是普通业务节点；
    - agent 是 LLM 决策节点；
    - tools 是工具执行节点；
    - agent 到 tools 是条件边；
    - tools 到 agent 是普通边，形成 ReAct 循环。
    """
    agent_node, route_after_agent = _build_nodes()

    # StateGraph(ReActState) 声明这张图使用哪一种 state schema。
    # 之后所有节点都会收到 ReActState，并返回 ReActState 的局部更新。
    builder = StateGraph(ReActState)

    # 添加两个节点：
    # 1. agent：我们自己定义的函数；
    # 2. tools：LangGraph 预置节点，专门执行 AIMessage.tool_calls。
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(DEFAULT_TOOLS))

    # 图从 START 进入 agent。第一次 agent 会看到用户输入的 HumanMessage。
    builder.add_edge(START, "agent")

    # agent 执行完以后，不是固定去下一个节点，而是交给 route_after_agent 判断：
    # - route_after_agent 返回 "tools" 时，走到 tools 节点；
    # - route_after_agent 返回 END 时，整张图结束。
    builder.add_conditional_edges("agent", route_after_agent, {"tools": "tools", END: END})

    # tools 执行完工具后，会把 ToolMessage 追加到 messages。
    # 然后回到 agent，让 LLM 观察工具结果并生成最终回答，或继续调用新工具。
    builder.add_edge("tools", "agent")

    return builder
