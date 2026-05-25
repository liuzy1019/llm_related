from app.domain.heuristics import detect_intent, extract_slots, normalize_text
from app.tools.business_tools import execute_business_action
from app.data import MOCK_DB


def test_normalize_text_corrects_domain_typo() -> None:
    assert normalize_text("订单123456吃出所料了") == "订单123456吃出塑料了"


def test_router_rules_detect_food_safety() -> None:
    intent, confidence = detect_intent("订单123456吃出塑料了")
    assert intent == "食安"
    assert confidence > 0.9


def test_extract_slots_reads_order_id() -> None:
    assert extract_slots("我的订单123456到哪了")["order_id"] == "123456"


def test_mutating_action_requires_confirmation() -> None:
    MOCK_DB.reset()
    result = execute_business_action("退款", {"order_id": "888888"})[-1]
    assert result["status"] == "needs_confirmation"
    assert result["requires_confirmation"] is True


def test_delivery_uses_mock_database() -> None:
    MOCK_DB.reset()
    result = execute_business_action("配送", {"order_id": "123456"})[0]
    assert result["delivery"]["courier_name"] == "周师傅"
    assert result["eta_minutes"] == 12
