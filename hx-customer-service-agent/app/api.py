"""FastAPI entrypoint for the Hx customer service agent."""

from __future__ import annotations

import time

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.agents import build_customer_service_graph
from app.data import MOCK_DB
from app.settings import settings

graph = build_customer_service_graph().compile()
app = FastAPI(title=settings.app_name)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    session_id: str = settings.default_session_id
    user_id: str = settings.default_user_id


class ChatResponse(BaseModel):
    reply: str
    intent: str
    route: str
    escalate: bool
    latency_ms: float
    trace: list[str]


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    start = time.perf_counter()
    result = graph.invoke(
        {
            "query": req.query,
            "session_id": req.session_id,
            "user_id": req.user_id,
            "iteration_count": 0,
        },
        config={"configurable": {"thread_id": req.session_id}},
    )
    return ChatResponse(
        reply=result["reply"],
        intent=result["intent"],
        route=result["route"],
        escalate=result.get("escalate", False),
        latency_ms=(time.perf_counter() - start) * 1000,
        trace=result.get("trace", []),
    )


@app.get("/demo/orders")
async def list_demo_orders() -> list[dict]:
    """Expose demo orders for presentations and quick manual testing."""
    return MOCK_DB.list_demo_orders()
