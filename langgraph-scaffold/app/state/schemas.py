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
    """ReAct Agent 状态。"""

    messages: Annotated[List[BaseMessage], add_messages]
    iteration_count: int  # 迭代计数器，防止无限循环


class PlanExecuteState(TypedDict, total=False):
    """Plan & Execute 状态。"""

    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple[str, str]], operator.add]  # 追加而非覆盖
    response: str


class MultiAgentState(TypedDict, total=False):
    """多 Agent 协作状态（Supervisor 模式）。"""

    messages: Annotated[List[BaseMessage], add_messages]
    next: str  # 下一个被路由到的 worker
    iteration_count: int
