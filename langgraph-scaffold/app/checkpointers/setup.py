"""Checkpointer 工厂

按环境变量 CHECKPOINTER 选择具体实现：
- memory：MemorySaver，进程内，重启丢失（开发用）
- sqlite：SqliteSaver，本地文件持久化（测试/单机用）
- postgres：PostgresSaver，生产级高可用（生产用）

文章原文重点提醒：生产环境不要使用 MemorySaver。
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from app.settings import settings


@contextmanager
def get_checkpointer() -> Iterator[object]:
    """以上下文管理器形式返回 checkpointer，方便统一管理资源生命周期。

    用法::

        with get_checkpointer() as cp:
            graph = builder.compile(checkpointer=cp)
            graph.invoke(...)
    """
    kind = settings.checkpointer
    if kind == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        yield MemorySaver()
        return

    if kind == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "未安装 langgraph-checkpoint-sqlite，请执行：pip install langgraph-checkpoint-sqlite"
            ) from e
        with SqliteSaver.from_conn_string(settings.sqlite_path) as cp:
            yield cp
        return

    if kind == "postgres":
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "未安装 langgraph-checkpoint-postgres，请执行：pip install langgraph-checkpoint-postgres psycopg[binary]"
            ) from e
        if not settings.postgres_dsn:
            raise RuntimeError("CHECKPOINTER=postgres 但未配置 POSTGRES_DSN 环境变量")
        with PostgresSaver.from_conn_string(settings.postgres_dsn) as cp:
            cp.setup()  # 首次运行自动建表
            yield cp
        return

    raise ValueError(f"未知的 CHECKPOINTER 配置: {kind!r}")
