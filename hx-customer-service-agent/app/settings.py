"""Typed settings for the Hx customer service agent."""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional in tests
    pass


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "hx-customer-service-agent")
    mock_mode: bool = _get_bool("MOCK_MODE", True)
    max_agent_loop_iterations: int = int(os.getenv("MAX_AGENT_LOOP_ITERATIONS", "3"))
    default_user_id: str = os.getenv("DEFAULT_USER_ID", "demo-user")
    default_session_id: str = os.getenv("DEFAULT_SESSION_ID", "demo-session")


settings = Settings()

