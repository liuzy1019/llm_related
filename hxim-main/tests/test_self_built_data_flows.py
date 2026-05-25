from app.data import MOCK_DB
from app.data.mock_database import DemoDelivery, DemoOrder
from app.service import ChatService
from app.session_store import SessionStore


def _service_with_self_built_orders(*orders: DemoOrder) -> ChatService:
    MOCK_DB.reset()
    for order in orders:
        MOCK_DB.upsert_demo_order(order)
    return ChatService(session_store=SessionStore())


def _order(
    order_id: str,
    *,
    status: str = "preparing",
    cancelable: bool = False,
    refund_eligible: bool = False,
    delivery: DemoDelivery | None = None,
) -> DemoOrder:
    return DemoOrder(
        order_id=order_id,
        user_id="test-user",
        merchant="自建测试档口",
        items=["测试套餐", "测试饮品"],
        amount_yuan=19.9,
        status=status,
        paid=True,
        cancelable=cancelable,
        refund_eligible=refund_eligible,
        delivery=delivery,
        insurance_enabled=False,
        tags=["self_built_test"],
        events=["测试数据初始化"],
    )


def test_self_built_non_refundable_after_sale_order_is_blocked() -> None:
    service = _service_with_self_built_orders(
        _order("990001", status="delivered", refund_eligible=False)
    )

    result = service.chat("订单990001漏发了，我要退款", session_id="self-refund", user_id="test-user")

    assert result["intent"] == "少送错送"
    assert result["route"] == "HYBRID"
    assert result["function_results"][0]["status"] == "ok"
    assert result["function_results"][-1]["status"] == "blocked"
    assert "不满足自动退款条件" in result["reply"]
    assert result["session"]["pending_mutation"] is None
    assert result["autoeval"]["problemSolved"] == "未解决"
    assert result["board_record"]["is_resolved"] == 0


def test_self_built_cancelable_order_confirmation_updates_mock_state() -> None:
    service = _service_with_self_built_orders(
        _order("990002", status="preparing", cancelable=True, refund_eligible=True)
    )

    first = service.chat("取消订单990002", session_id="self-cancel", user_id="test-user")
    assert first["session"]["pending_mutation"]["function"] == "cancel_order"
    assert first["board_record"]["is_resolved"] == 0

    confirmed = service.chat("确认", session_id="self-cancel", user_id="test-user")

    saved_order = MOCK_DB.get_order("990002")
    assert confirmed["function_results"][0]["status"] == "ok"
    assert confirmed["session"]["pending_mutation"] is None
    assert saved_order["status"] == "canceled"
    assert saved_order["cancelable"] is False
    assert "用户确认后系统已取消订单" in saved_order["events"]
    assert confirmed["autoeval"]["problemSolved"] == "已解决"


def test_self_built_parallel_pending_confirmations_are_session_isolated() -> None:
    service = _service_with_self_built_orders(
        _order("990101", status="preparing", cancelable=True, refund_eligible=True),
        _order("990102", status="preparing", cancelable=True, refund_eligible=True),
    )

    service.chat("取消订单990101", session_id="self-a", user_id="test-user")
    service.chat("取消订单990102", session_id="self-b", user_id="test-user")

    confirmed_a = service.chat("确认", session_id="self-a", user_id="test-user")
    canceled_b = service.chat("取消", session_id="self-b", user_id="test-user")

    order_a = MOCK_DB.get_order("990101")
    order_b = MOCK_DB.get_order("990102")
    assert confirmed_a["function_results"][0]["order_id"] == "990101"
    assert canceled_b["function_results"][0]["order_id"] == "990102"
    assert order_a["status"] == "canceled"
    assert order_b["status"] == "preparing"
    assert order_b["cancelable"] is True


def test_self_built_unknown_order_rush_returns_unresolved_not_found() -> None:
    service = _service_with_self_built_orders()

    result = service.chat("订单990404到哪了，帮我催单", session_id="self-missing", user_id="test-user")

    assert result["intent"] == "催单"
    assert result["route"] == "ACTION"
    assert result["function_results"][0]["status"] == "not_found"
    assert result["function_results"][1]["status"] == "not_found"
    assert "没有查到订单 990404" in result["reply"]
    assert result["autoeval"]["problemSolved"] == "未解决"
    assert result["annotation_record"]["hive_id"] == result["board_record"]["id"]
