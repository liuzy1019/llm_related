"""Plan & Execute Agent

对应文章 3.2 节。
- Planner: LLM 输出结构化计划 List[str]
- Executor: 用 ReAct 子 agent 执行单步
- Replanner: 判断是否完成，否则更新剩余计划
"""

from __future__ import annotations

from typing import Any, Dict, List, Union

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.llm import get_llm
from app.state.schemas import PlanExecuteState
from app.tools import DEFAULT_TOOLS


class Plan(BaseModel):
    """结构化输出：按顺序排列的执行步骤。"""

    steps: List[str] = Field(description="按顺序排列的执行步骤")


class Response(BaseModel):
    """终止：直接给出最终答案。"""

    response: str


class Act(BaseModel):
    """Replan 输出：要么继续执行新计划，要么给出最终答案。"""

    action: Union[Plan, Response] = Field(description="继续执行新计划 or 给出最终答案")


def _make_planner():
    llm = get_llm()
    return (
        ChatPromptTemplate.from_messages(
            [
                ("system", "你是任务规划专家，将目标拆解为具体可执行的步骤"),
                ("human", "目标：{objective}"),
            ]
        )
        | llm.with_structured_output(Plan)
    )


def _make_replanner():
    llm = get_llm()
    return (
        ChatPromptTemplate.from_template(
            "目标：{input}\n原计划：{plan}\n已完成：{past_steps}\n"
            "判断：任务完成则给出答案，否则更新剩余计划"
        )
        | llm.with_structured_output(Act)
    )


def _make_executor():
    """复用 prebuilt ReAct，作为单步执行器。"""
    from langgraph.prebuilt import create_react_agent

    return create_react_agent(get_llm(), tools=DEFAULT_TOOLS)


def build_plan_execute_graph():
    planner = _make_planner()
    replanner = _make_replanner()
    executor = _make_executor()

    def plan_step(state: PlanExecuteState) -> Dict[str, Any]:
        plan = planner.invoke({"objective": state["input"]})
        return {"plan": plan.steps}

    def execute_step(state: PlanExecuteState) -> Dict[str, Any]:
        plan = state.get("plan") or []
        if not plan:
            # 没有可执行步骤直接给空响应，避免死循环
            return {"response": "(无可执行步骤)"}
        current = plan[0]
        result = executor.invoke({"messages": [("human", current)]})
        return {"past_steps": [(current, result["messages"][-1].content)]}

    def replan_step(state: PlanExecuteState) -> Dict[str, Any]:
        out: Act = replanner.invoke(state)
        if isinstance(out.action, Response):
            return {"response": out.action.response}
        return {"plan": out.action.steps}

    def should_end(state: PlanExecuteState) -> str:
        return END if state.get("response") else "executor"

    builder = StateGraph(PlanExecuteState)
    builder.add_node("planner", plan_step)
    builder.add_node("executor", execute_step)
    builder.add_node("replanner", replan_step)
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "executor")
    builder.add_edge("executor", "replanner")
    builder.add_conditional_edges("replanner", should_end, {"executor": "executor", END: END})
    return builder
