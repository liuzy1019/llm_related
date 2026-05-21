"""Rule-based fallback for Router Agent.

These rules encode the current Hx design: typo correction, intent detection,
stage detection, emotion detection, escalation, slot extraction and routing.
They are intentionally deterministic so tests and demos can run without API keys.
"""

from __future__ import annotations

import re
from typing import Any

TYPO_MAP = {
    "吃出所料": "吃出塑料",
    "吃坏肚子": "吃坏了肚子",
    "退宽": "退款",
    "催一下单": "催单",
}

SENSITIVE_WORDS = ("315", "律师", "曝光", "监管", "投诉到底")
NEGATIVE_WORDS = ("生气", "太慢", "破平台", "差评", "恶心", "坏了", "投诉", "赔偿")
POSITIVE_WORDS = ("谢谢", "满意", "不错", "好吃", "辛苦")


def normalize_text(text: str) -> str:
    normalized = text.strip()
    for wrong, correct in TYPO_MAP.items():
        normalized = normalized.replace(wrong, correct)
    return normalized


def extract_slots(text: str) -> dict[str, Any]:
    slots: dict[str, Any] = {}
    order_match = re.search(r"(?:订单号?|单号)?\s*([0-9]{6,})", text)
    if order_match:
        slots["order_id"] = order_match.group(1)
    phone_match = re.search(r"1[3-9]\d{9}", text)
    if phone_match:
        slots["phone"] = phone_match.group(0)
    if "地址" in text or "送到" in text:
        slots["address_hint"] = True
    if any(word in text for word in ("塑料", "异物", "过敏", "肚子疼", "吃坏")):
        slots["safety_issue"] = True
    if any(word in text for word in ("少辣", "不辣", "花生", "香菜", "过敏")):
        slots["preference_hint"] = True
    return slots


def detect_intent(text: str) -> tuple[str, float]:
    keyword_rules: tuple[tuple[str, tuple[str, ...], float], ...] = (
        ("human_handoff", ("人工", "真人", "客服"), 0.96),
        ("food_safety", ("塑料", "异物", "吃坏", "肚子疼", "过敏"), 0.94),
        ("complaint", ("投诉", "赔偿", "315", "律师", "曝光"), 0.92),
        ("refund_request", ("退款", "退钱", "售后"), 0.9),
        ("order_cancel", ("取消订单", "不要了", "取消"), 0.88),
        ("order_rush", ("催单", "催一下", "快点", "还没送到"), 0.87),
        ("delivery_inquiry", ("到哪", "配送", "骑手", "多久到", "送到哪"), 0.86),
        ("wrong_item", ("送错", "错发"), 0.86),
        ("missing_item", ("漏发", "少送", "没给"), 0.86),
        ("order_modify", ("改地址", "加菜", "改备注", "修改订单"), 0.84),
        ("price_inquiry", ("多少钱", "价格", "优惠"), 0.82),
        ("product_inquiry", ("有什么菜", "推荐", "口味", "辣不辣", "菜单"), 0.82),
        ("business_hours", ("几点", "营业", "开门"), 0.8),
        ("greeting", ("你好", "您好", "hello"), 0.75),
    )
    for intent, keywords, confidence in keyword_rules:
        if any(keyword in text for keyword in keywords):
            return intent, confidence
    return "faq", 0.62


def detect_stage(intent: str) -> str:
    if intent in {"product_inquiry", "price_inquiry", "business_hours", "recommendation", "faq"}:
        return "presale"
    if intent in {"delivery_inquiry", "order_rush", "order_cancel", "order_modify"}:
        return "sale"
    if intent in {"refund_request", "wrong_item", "missing_item", "food_safety", "complaint"}:
        return "after_sale"
    return "general"


def detect_emotion(text: str) -> str:
    if any(word in text for word in NEGATIVE_WORDS):
        return "negative"
    if any(word in text for word in POSITIVE_WORDS):
        return "positive"
    return "neutral"


def should_escalate(text: str, intent: str, emotion: str, confidence: float) -> tuple[bool, str]:
    if intent == "human_handoff":
        return True, "user_requested_human"
    if intent == "food_safety":
        return True, "p0_food_safety"
    if any(word in text for word in SENSITIVE_WORDS):
        return True, "sensitive_keyword"
    if emotion == "negative" and confidence < 0.65:
        return True, "low_confidence_negative"
    return False, ""


def decide_route(intent: str, slots: dict[str, Any], escalate: bool) -> str:
    if escalate:
        return "ESCALATE"
    if intent in {"greeting", "goodbye", "chitchat"}:
        return "CHITCHAT"
    if intent in {"product_inquiry", "price_inquiry", "business_hours", "faq", "policy_inquiry"}:
        return "KNOWLEDGE"
    if intent in {"delivery_inquiry", "order_rush"} and slots.get("order_id"):
        return "ACTION"
    if intent in {
        "order_cancel",
        "refund_request",
        "wrong_item",
        "missing_item",
        "order_modify",
        "complaint",
        "food_safety",
    }:
        return "HYBRID"
    return "HYBRID"

