"""快速运行入口

示例::

    python scripts/run_agent.py --mode react --query "北京今天天气怎么样？顺便算一下 123*456"
    python scripts/run_agent.py --mode plan-execute --query "..."
    python scripts/run_agent.py --mode multi --query "..."

支持通过 --thread 指定会话 ID（持久化场景下决定状态隔离），默认 demo-001。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 把项目根加入 sys.path，便于直接 `python scripts/run_agent.py`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_core.messages import HumanMessage  # noqa: E402

from app.agents import (  # noqa: E402
    build_multi_agent_graph,
    build_plan_execute_graph,
    build_react_graph,
)
from app.checkpointers import get_checkpointer  # noqa: E402
from app.settings import banner  # noqa: E402


def _run_react(query: str, thread: str) -> None:
    builder = build_react_graph()
    with get_checkpointer() as cp:
        graph = builder.compile(checkpointer=cp)
        result = graph.invoke(
            {"messages": [HumanMessage(content=query)], "iteration_count": 0},
            config={"configurable": {"thread_id": thread}},
        )
    print("\n=== ReAct 最终回答 ===")
    print(result["messages"][-1].content)


def _run_plan_execute(query: str, thread: str) -> None:
    builder = build_plan_execute_graph()
    with get_checkpointer() as cp:
        graph = builder.compile(checkpointer=cp)
        result = graph.invoke(
            {"input": query},
            config={"configurable": {"thread_id": thread}},
        )
    print("\n=== Plan & Execute 最终回答 ===")
    print(result.get("response") or result)


def _run_multi(query: str, thread: str) -> None:
    builder = build_multi_agent_graph()
    with get_checkpointer() as cp:
        graph = builder.compile(checkpointer=cp)
        result = graph.invoke(
            {"messages": [HumanMessage(content=query)], "iteration_count": 0},
            config={"configurable": {"thread_id": thread}},
        )
    print("\n=== Multi-Agent 最终回答 ===")
    print(result["messages"][-1].content)


def main() -> None:
    parser = argparse.ArgumentParser(description="LangGraph 脚手架 - 三种模式快速运行入口")
    parser.add_argument(
        "--mode",
        choices=["react", "plan-execute", "multi"],
        default="react",
        help="选择 Agent 模式",
    )
    parser.add_argument("--query", required=True, help="用户问题 / 任务目标")
    parser.add_argument("--thread", default="demo-001", help="会话 ID（持久化隔离用）")
    args = parser.parse_args()

    print(banner())

    if args.mode == "react":
        _run_react(args.query, args.thread)
    elif args.mode == "plan-execute":
        _run_plan_execute(args.query, args.thread)
    else:
        _run_multi(args.query, args.thread)


if __name__ == "__main__":
    main()
