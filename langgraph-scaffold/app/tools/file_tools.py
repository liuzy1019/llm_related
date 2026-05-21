"""文件编辑工具。

仅允许写入运行入口显式声明的“当前文件”，用于演示 Agent 如何在受限范围内修改工作区文件。
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain_core.tools import tool

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CURRENT_FILE_ENV = "AGENT_CURRENT_FILE"
WORKSPACE_ROOT_ENV = "AGENT_WORKSPACE_ROOT"


def _workspace_root() -> Path:
    root = os.environ.get(WORKSPACE_ROOT_ENV)
    return Path(root).expanduser().resolve() if root else PROJECT_ROOT


def _resolve_current_file() -> Path:
    current_file = os.environ.get(CURRENT_FILE_ENV)
    if not current_file:
        raise ValueError(
            f"未设置当前文件。请运行 scripts/run_agent.py 时传入 --current-file，"
            f"或设置环境变量 {CURRENT_FILE_ENV}。"
        )

    path = Path(current_file).expanduser().resolve()
    root = _workspace_root()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"当前文件必须位于工作区内：{root}") from exc
    if not path.exists():
        raise ValueError(f"当前文件不存在：{path}")
    if not path.is_file():
        raise ValueError(f"当前路径不是文件：{path}")
    return path


@tool
def type_in_current_file(text: str) -> str:
    """把文本追加写入当前文件末尾；当前文件由 run_agent.py 的 --current-file 指定。"""
    try:
        if not text:
            return "写入失败：text 不能为空"
        path = _resolve_current_file()
        with path.open("a", encoding="utf-8") as f:
            f.write(text)
        return f"已向当前文件追加 {len(text)} 个字符：{path}"
    except Exception as e:  # noqa: BLE001
        return f"写入失败: {e}"
