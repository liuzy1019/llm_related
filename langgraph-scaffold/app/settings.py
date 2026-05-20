"""统一配置加载

读取 .env 中的环境变量并暴露为 typed 字段，供其余模块导入使用。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - 缺 dotenv 不应阻塞主流程
    pass


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # LLM
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    mock_llm: bool = _get_bool("MOCK_LLM", False)

    # Checkpointer
    checkpointer: str = os.getenv("CHECKPOINTER", "memory").lower()
    sqlite_path: str = os.getenv("SQLITE_PATH", "./.checkpoints.sqlite")
    postgres_dsn: str = os.getenv("POSTGRES_DSN", "")

    # LangSmith
    langsmith_enabled: bool = _get_bool("LANGCHAIN_TRACING_V2", False)
    langsmith_project: str = os.getenv("LANGCHAIN_PROJECT", "langgraph-scaffold")


settings = Settings()


def banner() -> str:
    """打印当前生效配置（敏感字段脱敏），方便启动时确认。"""
    api_mask = (
        settings.openai_api_key[:6] + "***" if settings.openai_api_key else "(empty)"
    )
    return (
        "[langgraph-scaffold] "
        f"model={settings.openai_model} "
        f"mock_llm={settings.mock_llm} "
        f"checkpointer={settings.checkpointer} "
        f"langsmith={settings.langsmith_enabled} "
        f"openai_key={api_mask}"
    )
