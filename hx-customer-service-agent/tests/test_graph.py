from app.agents import build_customer_service_graph


def _invoke(query: str) -> dict:
    graph = build_customer_service_graph().compile()
    return graph.invoke(
        {
            "query": query,
            "session_id": "test-session",
            "user_id": "test-user",
            "iteration_count": 0,
        },
        config={"configurable": {"thread_id": "test-session"}},
    )


def test_delivery_rush_uses_action_route() -> None:
    result = _invoke("我的订单123456到哪了，帮我催一下")
    assert result["intent"] == "order_rush"
    assert result["route"] == "ACTION"
    assert "催单" in result["reply"]


def test_food_safety_escalates_to_human() -> None:
    result = _invoke("订单123456吃出所料了，我肚子疼")
    assert result["intent"] == "food_safety"
    assert result["route"] == "ESCALATE"
    assert result["escalate"] is True
    assert "人工客服" in result["reply"]


def test_refund_missing_order_asks_for_order_id() -> None:
    result = _invoke("我要退款")
    assert result["intent"] == "refund_request"
    assert result["route"] == "HYBRID"
    assert "order_id" in result["reply"]


def test_cancel_order_uses_cancelable_demo_order() -> None:
    result = _invoke("取消订单888888")
    assert result["intent"] == "order_cancel"
    assert result["route"] == "HYBRID"
    assert "二次确认" in result["reply"]
