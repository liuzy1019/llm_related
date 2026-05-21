"""State schemas.

The graph follows the same style as ``langgraph-scaffold``: keep the shared
state in one module, return partial updates from nodes, and use reducers for
append-only fields.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class CustomerServiceState(TypedDict, total=False):
    """Shared state for the Hx canteen customer service workflow."""

    query: str
    session_id: str
    user_id: str

    normalized_query: str
    memory_snapshot: dict[str, Any]

    intent: str
    stage: str
    emotion: str
    confidence: float
    route: str
    escalate: bool
    escalate_reason: str

    slots: dict[str, Any]
    rag_results: Annotated[list[dict[str, Any]], operator.add]
    function_results: Annotated[list[dict[str, Any]], operator.add]

    reply: str
    memory_updates: dict[str, Any]
    trace: Annotated[list[str], operator.add]
    iteration_count: int

