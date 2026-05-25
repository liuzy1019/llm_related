"""Small offline catalog used by Knowledge Agent and tests.

Production can replace this module with ChromaDB collections:
products / faq / policies, matching the two Hx design documents.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeItem:
    collection: str
    title: str
    content: str
    intents: tuple[str, ...]


KNOWLEDGE_BASE: tuple[KnowledgeItem, ...] = (
    KnowledgeItem(
        collection="faq",
        title="营业时间",
        content="浣熊食堂午餐 10:30-14:00，晚餐 16:30-20:30；高峰期配送可能延迟 10-20 分钟。",
        intents=("门店", "澄清"),
    ),
    KnowledgeItem(
        collection="products",
        title="菜品口味",
        content="默认口味偏清淡，可备注少辣、不辣、少油；过敏信息建议在下单备注中明确填写。",
        intents=("商品", "备注"),
    ),
    KnowledgeItem(
        collection="policies",
        title="退款规则",
        content="未出餐订单可申请取消；已出餐订单需按错发、漏发、食品质量等原因提交售后。",
        intents=("退款", "少送错送", "餐品不符合预期", "餐损撒漏"),
    ),
    KnowledgeItem(
        collection="policies",
        title="食品安全处理",
        content="疑似异物、过敏或身体不适属于 P0 场景，应保留照片和订单信息，并优先转人工跟进。",
        intents=("食安",),
    ),
    KnowledgeItem(
        collection="faq",
        title="配送查询",
        content="配送状态可通过订单号查询；若预计送达时间异常，可发起催单通知商家和骑手。",
        intents=("配送", "催单"),
    ),
)


def search_knowledge(intent: str, query: str, limit: int = 3) -> list[dict[str, str]]:
    """Return deterministic top-k knowledge snippets for offline mode."""
    query = query or ""
    ranked: list[tuple[int, KnowledgeItem]] = []
    for item in KNOWLEDGE_BASE:
        score = 0
        if intent in item.intents:
            score += 3
        if any(token in item.content for token in ("退款", "取消", "配送", "过敏", "异物") if token in query):
            score += 1
        if score:
            ranked.append((score, item))

    if not ranked:
        ranked = [(1, item) for item in KNOWLEDGE_BASE if "faq" == item.collection]

    ranked.sort(key=lambda row: row[0], reverse=True)
    return [
        {
            "collection": item.collection,
            "title": item.title,
            "content": item.content,
        }
        for _, item in ranked[:limit]
    ]
