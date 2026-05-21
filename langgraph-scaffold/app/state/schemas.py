"""State schemas

集中定义所有 Agent 用到的 TypedDict，配合 add_messages / operator.add 等归约函数，
避免节点返回值覆盖历史数据（这是文章中重点强调的高频踩坑）。
"""

from __future__ import annotations

import operator
from typing import Annotated, List, Tuple, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ReActState(TypedDict, total=False):
    """ReAct Agent 状态。

    LangGraph 每次执行节点时都会传入整份 state，节点只返回需要更新的字段。
    返回值如何合并回 state，由字段上的 reducer 决定。
    """

    # add_messages 表示“把新消息追加到旧消息后面”，这是聊天/工具调用历史的核心。
    messages: Annotated[List[BaseMessage], add_messages]
    iteration_count: int  # 迭代计数器，防止无限循环


class PlanExecuteState(TypedDict, total=False):
    """Plan & Execute 状态。

    input 是原始任务；plan 是待执行计划；past_steps 是已经完成的步骤记录；
    response 一旦出现，就表示整张图可以结束。
    """

    input: str
    plan: List[str]
    # operator.add 表示每次 executor 返回的新步骤会追加到历史列表，而不是覆盖。
    past_steps: Annotated[List[Tuple[str, str]], operator.add]  # 追加而非覆盖
    response: str


class MultiAgentState(TypedDict, total=False):
    """多 Agent 协作状态（Supervisor 模式）。

    supervisor 通过 next 字段决定下一跳去 researcher、calculator 还是结束。
    """

    messages: Annotated[List[BaseMessage], add_messages]
    next: str  # 下一个被路由到的 worker
    iteration_count: int
