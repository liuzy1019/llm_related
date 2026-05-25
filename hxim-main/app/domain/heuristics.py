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
    if "取消订单" in text or "取消" in text or "不要了" in text:
        slots["requested_action"] = "cancel_order"
    return slots


def detect_intent(text: str) -> tuple[str, float]:
    keyword_rules: tuple[tuple[str, tuple[str, ...], float], ...] = (
        ("转人工", ("人工", "真人", "客服"), 0.96),
        ("食安", ("塑料", "异物", "吃坏", "肚子疼", "过期", "变质", "虫子"), 0.94),
        ("少送错送", ("漏发", "少送", "没给", "送错", "错发", "少了一份"), 0.9),
        ("餐损撒漏", ("洒了", "撒了", "漏了", "外溢", "包装破", "包装坏", "汤洒"), 0.89),
        ("餐品不符合预期", ("太咸", "太淡", "凉了", "不热", "难吃", "分量少", "不好吃"), 0.88),
        ("退款", ("退款", "退钱", "售后", "取消订单", "不要了", "取消"), 0.9),
        ("催单", ("催单", "催一下", "快点", "还没送到", "怎么还没", "什么时候到", "多久到", "到哪"), 0.87),
        ("配送", ("放门口", "放柜子", "别放", "不要放", "送到", "骑手", "配送", "注意安全"), 0.86),
        ("修改订单", ("改地址", "修改订单", "换商品", "更换商品", "改电话"), 0.84),
        ("备注", ("不要辣", "加辣", "少辣", "不辣", "不要香菜", "多放", "少放", "备注"), 0.84),
        ("发票", ("发票", "抬头", "税号"), 0.83),
        ("团餐", ("团餐", "公司订餐", "大额订单", "50份", "二十份", "20份", "十份", "10份"), 0.83),
        ("赠品", ("送个", "赠品", "免费送", "能送"), 0.82),
        ("优惠", ("多少钱", "价格", "优惠", "折扣", "满减", "券", "会员"), 0.82),
        ("商品", ("有什么菜", "推荐", "口味", "辣不辣", "菜单", "原料", "售罄", "补货"), 0.82),
        ("门店", ("几点", "营业", "开门", "地址", "在哪", "电话", "预定", "浣熊食堂"), 0.8),
        ("闲聊", ("你好", "您好", "hello", "谢谢", "辛苦了"), 0.75),
    )
    for intent, keywords, confidence in keyword_rules:
        if any(keyword in text for keyword in keywords):
            return intent, confidence
    return "澄清", 0.62


def detect_stage(intent: str) -> str:
    if intent in {"商品", "优惠", "门店", "团餐", "赠品", "发票", "澄清"}:
        return "presale"
    if intent in {"配送", "催单", "修改订单", "备注"}:
        return "sale"
    if intent in {"退款", "少送错送", "食安", "餐损撒漏", "餐品不符合预期"}:
        return "after_sale"
    return "general"


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
    if intent == "闲聊":
        return "CHITCHAT"
    if intent in {"商品", "优惠", "门店", "团餐", "赠品", "发票", "澄清"}:
        return "KNOWLEDGE"
    if intent in {"配送", "催单"} and slots.get("order_id"):
        return "ACTION"
    if intent in {"退款", "少送错送", "食安", "餐损撒漏", "餐品不符合预期", "修改订单", "备注"}:
        return "HYBRID"
    return "HYBRID"
