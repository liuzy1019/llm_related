"""Rule-based fallback for Router Agent.

These rules encode the current Hx design: typo correction, intent detection,
stage detection, emotion detection, escalation, slot extraction and routing.
They are intentionally deterministic so tests and demos can run without API keys.
"""

from __future__ import annotations

import re
from typing import Any

from app.domain.config_loader import (
    get_default_confidence,
    get_default_intent,
    get_intent_rule,
    iter_intent_rules,
)

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
    if "取消订单" in text or "取消" in text or "不要了" in text:
        slots["requested_action"] = "cancel_order"
    return slots


def detect_intent(text: str) -> tuple[str, float]:
    for rule in iter_intent_rules():
        keywords = tuple(rule.get("keywords", ()))
        if keywords and any(keyword in text for keyword in keywords):
            return str(rule["name"]), float(rule["confidence"])
    return get_default_intent(), get_default_confidence()


def detect_stage(intent: str) -> str:
    rule = get_intent_rule(intent)
    return str(rule.get("stage", "general")) if rule else "general"


def detect_emotion(text: str) -> str:
    if any(word in text for word in NEGATIVE_WORDS):
        return "negative"
    if any(word in text for word in POSITIVE_WORDS):
        return "positive"
    return "neutral"


def should_escalate(text: str, intent: str, emotion: str, confidence: float) -> tuple[bool, str]:
    if intent == "转人工":
        return True, "user_requested_human"
    if intent == "食安":
        return True, "p0_food_safety"
    if any(word in text for word in SENSITIVE_WORDS):
        return True, "sensitive_keyword"
    if emotion == "negative" and confidence < 0.65:
        return True, "low_confidence_negative"
    return False, ""


def decide_route(intent: str, slots: dict[str, Any], escalate: bool) -> str:
    if escalate:
        return "ESCALATE"
    rule = get_intent_rule(intent)
    if not rule:
        return "HYBRID"
    if rule.get("requires_order_id_for_route") and not slots.get("order_id"):
        return str(rule.get("missing_order_route", "HYBRID"))
    return str(rule.get("route", "HYBRID"))
