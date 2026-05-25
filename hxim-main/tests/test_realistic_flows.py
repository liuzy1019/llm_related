from app.service import ChatService
from app.session_store import SessionStore
from app.data import MOCK_DB


def _service() -> ChatService:
    MOCK_DB.reset()
    return ChatService(session_store=SessionStore())


def test_realistic_refund_flow_with_interleaved_knowledge_question() -> None:
    service = _service()

    first = service.chat("我要退款", session_id="flow-refund", user_id="demo-user")
    assert first["reply"] == "我可以继续处理，请先补充：order_id"
    assert first["session"]["pending_intent"] == "退款"

    knowledge = service.chat("你们几点营业", session_id="flow-refund", user_id="demo-user")
    assert knowledge["intent"] == "门店"
    assert knowledge["route"] == "KNOWLEDGE"
    assert "10:30-14:00" in knowledge["reply"]
    assert knowledge["session"]["pending_intent"] is None

    restarted = service.chat("我要退款", session_id="flow-refund", user_id="demo-user")
    assert restarted["session"]["pending_intent"] == "退款"

    completed = service.chat("778899", session_id="flow-refund", user_id="demo-user")
    assert completed["intent"] == "退款"
    assert completed["slots"]["order_id"] == "778899"
    assert "订单 778899 金额 24.0 元" in completed["reply"]
    assert completed["session"]["pending_intent"] is None
    assert completed["session"]["pending_mutation"]["function"] == "submit_refund"

    confirmed = service.chat("确认", session_id="flow-refund", user_id="demo-user")
    assert "工单号" in confirmed["reply"]
    assert confirmed["session"]["pending_mutation"] is None
    assert confirmed["session"]["turn_count"] == 5


def test_realistic_parallel_sessions_are_isolated() -> None:
    service = _service()

    refund_first = service.chat("我要退款", session_id="session-a", user_id="demo-user")
    assert refund_first["session"]["pending_intent"] == "退款"

    rush_first = service.chat("帮我催单", session_id="session-b", user_id="demo-user")
    assert rush_first["session"]["pending_intent"] == "催单"

    refund_done = service.chat("778899", session_id="session-a", user_id="demo-user")
    assert refund_done["intent"] == "退款"
    assert "退款申请" in refund_done["reply"]
    assert refund_done["session"]["pending_mutation"]["function"] == "submit_refund"

    rush_done = service.chat("123456", session_id="session-b", user_id="demo-user")
    assert rush_done["intent"] == "催单"
    assert "催单" in rush_done["reply"]


def test_realistic_reset_prevents_stale_intent_carryover() -> None:
    service = _service()

    service.chat("帮我催单", session_id="flow-reset", user_id="demo-user")
    service.reset("flow-reset")

    result = service.chat("123456", session_id="flow-reset", user_id="demo-user")
    assert result["intent"] == "澄清"
    assert result["route"] == "KNOWLEDGE"
    assert result["session"]["pending_intent"] is None


def test_realistic_food_safety_interrupt_clears_previous_pending_task() -> None:
    service = _service()

    first = service.chat("我要退款", session_id="flow-safety", user_id="demo-user")
    assert first["session"]["pending_intent"] == "退款"

    safety = service.chat("订单123456吃出所料了，我肚子疼", session_id="flow-safety", user_id="demo-user")
    assert safety["intent"] == "食安"
    assert safety["route"] == "ESCALATE"
    assert safety["escalate"] is True
    assert "人工客服" in safety["reply"]
    assert safety["session"]["pending_intent"] is None


def test_realistic_session_can_continue_after_completed_turn() -> None:
    service = _service()

    service.chat("帮我催单", session_id="flow-after-complete", user_id="demo-user")
    rush = service.chat("123456", session_id="flow-after-complete", user_id="demo-user")
    assert rush["session"]["pending_intent"] is None

    hours = service.chat("你们几点营业", session_id="flow-after-complete", user_id="demo-user")
    assert hours["intent"] == "门店"
    assert hours["route"] == "KNOWLEDGE"
    assert hours["session"]["pending_intent"] is None
