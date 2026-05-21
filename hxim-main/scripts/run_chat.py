"""CLI runner for the Hx customer service agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agents import build_customer_service_graph  # noqa: E402
from app.settings import settings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Hx customer service agent")
    parser.add_argument("--query", required=True, help="用户消息")
    parser.add_argument("--session-id", default=settings.default_session_id)
    parser.add_argument("--user-id", default=settings.default_user_id)
    args = parser.parse_args()

    graph = build_customer_service_graph().compile()
    result = graph.invoke(
        {
            "query": args.query,
            "session_id": args.session_id,
            "user_id": args.user_id,
            "iteration_count": 0,
        },
        config={"configurable": {"thread_id": args.session_id}},
    )

    print("=== Reply ===")
    print(result["reply"])
    print("\n=== Debug ===")
    print(
        {
            "intent": result.get("intent"),
            "route": result.get("route"),
            "slots": result.get("slots"),
            "trace": result.get("trace"),
        }
    )


if __name__ == "__main__":
    main()

