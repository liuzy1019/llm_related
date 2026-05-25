"""CLI runner for the Hx customer service agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.service import ChatService  # noqa: E402
from app.settings import settings  # noqa: E402


def _print_result(result: dict) -> None:
    print("=== Reply ===")
    print(result["reply"])
    print("\n=== Debug ===")
    print(
        {
            "intent": result.get("intent"),
            "route": result.get("route"),
            "slots": result.get("slots"),
            "session": result.get("session"),
            "autoeval": result.get("autoeval"),
            "board_record": result.get("board_record"),
            "annotation_record": result.get("annotation_record"),
            "trace": result.get("trace"),
        }
    )


def _run_interactive(service: ChatService, session_id: str, user_id: str) -> None:
    print(f"Interactive mode. session_id={session_id}. 输入 exit/quit 退出。")
    while True:
        try:
            query = input("你: ").strip()
        except EOFError:
            break
        if query.lower() in {"exit", "quit"}:
            break
        if not query:
            continue
        _print_result(service.chat(query, session_id, user_id))
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Hx customer service agent")
    parser.add_argument("--query", help="用户消息")
    parser.add_argument("--session-id", default=settings.default_session_id)
    parser.add_argument("--user-id", default=settings.default_user_id)
    parser.add_argument("--interactive", action="store_true", help="连续对话模式")
    args = parser.parse_args()

    service = ChatService()
    if args.interactive:
        _run_interactive(service, args.session_id, args.user_id)
        return
    if not args.query:
        parser.error("--query is required unless --interactive is set")
    _print_result(service.chat(args.query, args.session_id, args.user_id))


if __name__ == "__main__":
    main()
