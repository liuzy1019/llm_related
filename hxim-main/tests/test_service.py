from app.service import ChatService
from app.session_store import SessionStore
from app.data import MOCK_DB


def _service() -> ChatService:
    MOCK_DB.reset()
    return ChatService(session_store=SessionStore())


def test_refund_missing_order_continues_with_order_id() -> None:
    service = _service()
    first = service.chat("我要退款", session_id="s-refund", user_id="demo-user")
    assert first["intent"] == "退款"
    assert first["session"]["pending_intent"] == "退款"
    assert first["session"]["missing_slots"] == ["order_id"]

    second = service.chat("778899", session_id="s-refund", user_id="demo-user")
    assert second["intent"] == "退款"
    assert second["slots"]["order_id"] == "778899"
    assert "退款申请" in second["reply"]
    assert second["session"]["pending_intent"] is None
    assert second["session"]["pending_mutation"]["function"] == "submit_refund"
    assert second["autoeval"]["intent"] == "退款"
    assert second["board_record"]["intent"] == "【退款】"
    assert "session_data_string" in second["board_record"]
    assert second["autoeval"]["ModelOut"]["hxIntentDO"]["intent"] == "退款"
    assert second["board_record"]["date"].isdigit()
    assert len(second["board_record"]["date"]) == 8
    assert second["board_record"]["dt"] == second["board_record"]["date"]
    assert isinstance(second["board_record"]["create_time"], str)
    assert second["annotation_record"]["hive_id"] == second["board_record"]["id"]
    assert second["annotation_record"]["update_time"] == second["board_record"]["update_time"]

    confirmed = service.chat("确认", session_id="s-refund", user_id="demo-user")
    assert confirmed["intent"] == "退款"
    assert confirmed["session"]["pending_mutation"] is None
    assert confirmed["function_results"][0]["status"] == "ok"
    assert "工单号" in confirmed["reply"]


def test_rush_order_missing_order_continues_with_order_id() -> None:
    service = _service()
    first = service.chat("帮我催单", session_id="s-rush", user_id="demo-user")
    assert first["intent"] == "催单"
    assert first["session"]["missing_slots"] == ["order_id"]

    second = service.chat("123456", session_id="s-rush", user_id="demo-user")
    assert second["intent"] == "催单"
    assert second["route"] == "ACTION"
    assert "催单" in second["reply"]


def test_cancel_order_confirmation_commits_mock_mutation() -> None:
    service = _service()
    first = service.chat("取消订单888888", session_id="s-cancel", user_id="demo-user")
    assert first["intent"] == "退款"
    assert first["slots"]["requested_action"] == "cancel_order"
    assert first["session"]["pending_mutation"]["function"] == "cancel_order"
    assert "二次确认" in first["reply"] or "确认" in first["reply"]

    confirmed = service.chat("确认", session_id="s-cancel", user_id="demo-user")
    assert confirmed["session"]["pending_mutation"] is None
    assert confirmed["function_results"][0]["status"] == "ok"
    assert "已为你取消订单 888888" in confirmed["reply"]


def test_cancel_pending_mutation_clears_without_commit() -> None:
    service = _service()
    first = service.chat("取消订单888888", session_id="s-cancel-no", user_id="demo-user")
    assert first["session"]["pending_mutation"]["function"] == "cancel_order"

    canceled = service.chat("取消", session_id="s-cancel-no", user_id="demo-user")
    assert canceled["session"]["pending_mutation"] is None
    assert canceled["function_results"][0]["status"] == "canceled"
    assert "不会继续提交" in canceled["reply"]


def test_reset_clears_pending_state() -> None:
    service = _service()
    service.chat("我要退款", session_id="s-reset", user_id="demo-user")
    assert service.reset("s-reset") == {"status": "ok", "session_id": "s-reset"}

    result = service.chat("778899", session_id="s-reset", user_id="demo-user")
    assert result["intent"] != "退款"
    assert result["session"]["pending_intent"] is None
    assert result["session"]["pending_mutation"] is None
