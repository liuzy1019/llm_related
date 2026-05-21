"""快速运行入口

示例::

    python scripts/run_agent.py --mode react --query "北京今天天气怎么样？顺便算一下 123*456"
    python scripts/run_agent.py --mode plan-execute --query "..."
    python scripts/run_agent.py --mode multi --query "..."

支持通过 --thread 指定会话 ID（持久化场景下决定状态隔离），默认 demo-001。
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path

# 把项目根加入 sys.path，便于直接 `python scripts/run_agent.py`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_showwarning = warnings.showwarning


def _hide_known_langgraph_warning(message, category, filename, lineno, file=None, line=None):
    if "The default value of `allowed_objects` will change" in str(message):
        return
    _showwarning(message, category, filename, lineno, file=file, line=line)


warnings.showwarning = _hide_known_langgraph_warning

from langchain_core.messages import HumanMessage  # noqa: E402

from app.agents import (  # noqa: E402
    build_multi_agent_graph,
    build_plan_execute_graph,
    build_react_graph,
)
from app.checkpointers import get_checkpointer  # noqa: E402
from app.settings import banner  # noqa: E402


def _prepare_current_file(current_file: str | None) -> Path | None:
    """把 CLI 传入的当前文件写入环境变量，供文件工具读取。"""
    current_file = current_file or os.environ.get("AGENT_CURRENT_FILE")
    if not current_file:
        return None

    path = Path(current_file).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()

    os.environ["AGENT_CURRENT_FILE"] = str(path)
    os.environ.setdefault("AGENT_WORKSPACE_ROOT", str(ROOT))
    return path


def _with_current_file_context(query: str, current_file: Path | None) -> str:
    if current_file is None:
        return query
    return (
        f"当前文件路径：{current_file}\n"
        "工具提示：type_in_current_file 可处理当前文件编辑任务。\n"
        f"用户任务：{query}"
    )


def _run_react(query: str, thread: str) -> None:
    """运行手写 ReAct 图：适合观察 LLM -> 工具 -> LLM 的循环。"""
    builder = build_react_graph()
    with get_checkpointer() as cp:
        # compile 时传入 checkpointer；invoke 时用 thread_id 隔离不同会话。
        graph = builder.compile(checkpointer=cp)
        result = graph.invoke(
            {"messages": [HumanMessage(content=query)], "iteration_count": 0},
            config={"configurable": {"thread_id": thread}},
        )
    print("\n=== ReAct 最终回答 ===")
    print(result["messages"][-1].content)


def _run_plan_execute(query: str, thread: str) -> None:
    """运行 Plan & Execute 图：适合观察 plan/past_steps/response 三类状态。"""
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
    """运行 Supervisor 多 Agent 图：适合观察 next 字段如何控制 worker 路由。"""
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
    parser.add_argument(
        "--current-file",
        help="当前正在编辑的文件路径；传入后 Agent 可通过受限工具向该文件追加文本",
    )
    args = parser.parse_args()

    current_file = _prepare_current_file(args.current_file)
    query = _with_current_file_context(args.query, current_file)

    print(banner())
    if current_file:
        print(f"当前文件：{current_file}")

    # 选择模式
    if args.mode == "react":
        _run_react(query, args.thread)
    elif args.mode == "plan-execute":
        _run_plan_execute(query, args.thread)
    else:
        _run_multi(query, args.thread)


if __name__ == "__main__":
    main()
