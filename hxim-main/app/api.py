"""FastAPI entrypoint for the Hx customer service agent."""

from __future__ import annotations

import time

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.data import MOCK_DB
from app.service import CHAT_SERVICE
from app.settings import settings

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
    session: dict
    autoeval: dict
    board_record: dict
    annotation_record: dict
    evaluation_meta: dict


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    start = time.perf_counter()
    result = CHAT_SERVICE.chat(req.query, req.session_id, req.user_id)
    return ChatResponse(
        reply=result["reply"],
        intent=result["intent"],
        route=result["route"],
        escalate=result.get("escalate", False),
        latency_ms=(time.perf_counter() - start) * 1000,
        trace=result.get("trace", []),
        session=result.get("session", {}),
        autoeval=result.get("autoeval", {}),
        board_record=result.get("board_record", {}),
        annotation_record=result.get("annotation_record", {}),
        evaluation_meta=result.get("evaluation_meta", {}),
    )


@app.get("/demo/orders")
async def list_demo_orders() -> list[dict]:
    """Expose demo orders for presentations and quick manual testing."""
    return MOCK_DB.list_demo_orders()


@app.post("/reset/{session_id}")
async def reset_session(session_id: str) -> dict[str, str]:
    """Reset one demo conversation session."""
    return CHAT_SERVICE.reset(session_id)
