from app.domain.config_loader import (
    get_action_sequence,
    get_intent_rule,
    get_sop_text,
    iter_intent_rules,
    load_function_config,
    load_intent_config,
    load_sop_config,
)
from app.domain.heuristics import decide_route, detect_intent, detect_stage, extract_slots
from app.domain.im_standards import IM_INTENTS


def test_intent_config_covers_standard_intents() -> None:
    load_intent_config()

    configured = {rule["name"] for rule in iter_intent_rules()}

    assert set(IM_INTENTS) <= configured
    assert get_intent_rule("退款")["stage"] == "after_sale"
    assert get_intent_rule("门店")["route"] == "KNOWLEDGE"


def test_function_config_references_known_functions() -> None:
    config = load_function_config()

    function_names = set(config["functions"])
    for actions in config["action_sequences"].values():
        assert set(actions) <= function_names
    for override in config["slot_overrides"]:
        assert set(override["actions"]) <= function_names


def test_config_driven_router_preserves_core_routes() -> None:
    rush_intent, rush_confidence = detect_intent("我的订单123456到哪了，帮我催一下")
    rush_slots = extract_slots("我的订单123456到哪了，帮我催一下")
    hours_intent, _ = detect_intent("你们几点营业")

    assert rush_intent == "催单"
    assert rush_confidence == get_intent_rule("催单")["confidence"]
    assert detect_stage(rush_intent) == "sale"
    assert decide_route(rush_intent, rush_slots, escalate=False) == "ACTION"
    assert decide_route("催单", {}, escalate=False) == "HYBRID"
    assert hours_intent == "门店"
    assert decide_route(hours_intent, {}, escalate=False) == "KNOWLEDGE"


def test_config_driven_action_sequences_preserve_business_plan() -> None:
    assert get_action_sequence("催单", {"order_id": "123456"}) == (
        "query_delivery_status",
        "rush_order",
    )
    assert get_action_sequence("退款", {"order_id": "778899"}) == (
        "query_order",
        "submit_refund",
    )
    assert get_action_sequence(
        "退款",
        {"order_id": "888888", "requested_action": "cancel_order"},
    ) == ("cancel_order",)
    assert get_action_sequence("澄清", {}) == ("query_order",)


def test_sop_config_supplies_generator_text() -> None:
    load_sop_config()

    assert get_sop_text("generator", "missing_slots_prefix") == "我可以继续处理，请先补充："
    assert get_sop_text("escalation", "default_reply").startswith("这个问题")
