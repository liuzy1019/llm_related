"""In-memory demo database.

The demo keeps order, delivery, user profile and insurance data in one small
repository object. Business tools depend on this module instead of hard-coded
responses, so the demo can show realistic state lookup without a real database.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class DemoUser:
    user_id: str
    name: str
    phone_masked: str
    default_address: str
    preferences: dict[str, str] = field(default_factory=dict)
    allergies: list[str] = field(default_factory=list)


@dataclass
class DemoDelivery:
    courier_name: str
    courier_phone_masked: str
    distance_km: float
    eta_minutes: int
    status: str
    last_event: str


@dataclass
class DemoOrder:
    order_id: str
    user_id: str
    merchant: str
    items: list[str]
    amount_yuan: float
    status: str
    paid: bool
    cancelable: bool
    refund_eligible: bool
    delivery: DemoDelivery | None = None
    insurance_enabled: bool = False
    tags: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    rushed: bool = False
    refund_ticket_id: str | None = None


class MockCanteenDatabase:
    """Small repository that mimics the order-system boundary."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._users: dict[str, DemoUser] = {
            "demo-user": DemoUser(
                user_id="demo-user",
                name="李同学",
                phone_masked="138****6789",
                default_address="A 座 3 层前台",
                preferences={"spicy": "less_spicy"},
                allergies=["花生"],
            ),
            "test-user": DemoUser(
                user_id="test-user",
                name="测试用户",
                phone_masked="139****0000",
                default_address="测试楼 1 层",
            ),
        }
        self._orders: dict[str, DemoOrder] = {
            "123456": DemoOrder(
                order_id="123456",
                user_id="demo-user",
                merchant="浣熊食堂一号窗口",
                items=["番茄牛腩饭", "冰柠茶"],
                amount_yuan=36.5,
                status="delivering",
                paid=True,
                cancelable=False,
                refund_eligible=True,
                delivery=DemoDelivery(
                    courier_name="周师傅",
                    courier_phone_masked="136****2468",
                    distance_km=1.2,
                    eta_minutes=12,
                    status="picked_up",
                    last_event="骑手已取餐，正在配送中",
                ),
                insurance_enabled=True,
                tags=["hot_order"],
                events=["10:38 下单", "10:45 商家接单", "10:58 骑手取餐"],
            ),
            "888888": DemoOrder(
                order_id="888888",
                user_id="demo-user",
                merchant="轻食沙拉档口",
                items=["鸡胸肉沙拉"],
                amount_yuan=28.0,
                status="preparing",
                paid=True,
                cancelable=True,
                refund_eligible=True,
                delivery=None,
                events=["11:12 下单", "11:13 商家接单"],
            ),
            "778899": DemoOrder(
                order_id="778899",
                user_id="demo-user",
                merchant="面点窗口",
                items=["牛肉面", "卤蛋"],
                amount_yuan=24.0,
                status="delivered",
                paid=True,
                cancelable=False,
                refund_eligible=True,
                delivery=DemoDelivery(
                    courier_name="陈师傅",
                    courier_phone_masked="135****5678",
                    distance_km=0.0,
                    eta_minutes=0,
                    status="delivered",
                    last_event="订单已送达",
                ),
                insurance_enabled=False,
                tags=["after_sale"],
                events=["12:03 下单", "12:34 送达"],
            ),
        }
        self._ticket_sequence = 1000

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        user = self._users.get(user_id)
        return asdict(user) if user else None

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        order = self._orders.get(order_id)
        return asdict(deepcopy(order)) if order else None

    def list_demo_orders(self) -> list[dict[str, Any]]:
        return [asdict(deepcopy(order)) for order in self._orders.values()]

    def upsert_demo_order(self, order: DemoOrder) -> None:
        """Seed or replace one demo order for local verification and tests."""
        self._orders[order.order_id] = deepcopy(order)

    def mark_rushed(self, order_id: str) -> dict[str, Any] | None:
        order = self._orders.get(order_id)
        if not order:
            return None
        order.rushed = True
        order.events.append("系统已发送催单提醒")
        return asdict(deepcopy(order))

    def cancel_order(self, order_id: str) -> dict[str, Any] | None:
        order = self._orders.get(order_id)
        if not order or not order.cancelable:
            return None
        order.status = "canceled"
        order.cancelable = False
        order.refund_eligible = False
        order.events.append("用户确认后系统已取消订单")
        return asdict(deepcopy(order))

    def submit_refund(self, order_id: str, reason: str) -> dict[str, Any] | None:
        order = self._orders.get(order_id)
        if not order or not order.refund_eligible:
            return None
        self._ticket_sequence += 1
        ticket_id = f"TK{self._ticket_sequence}"
        order.refund_ticket_id = ticket_id
        order.events.append(f"用户确认后系统已提交退款申请，原因：{reason}")
        return {
            "ticket_id": ticket_id,
            "order_id": order_id,
            "type": "refund",
            "reason": reason,
            "status": "submitted",
        }

    def record_order_event(self, order_id: str, event: str) -> dict[str, Any] | None:
        order = self._orders.get(order_id)
        if not order:
            return None
        order.events.append(event)
        return asdict(deepcopy(order))


MOCK_DB = MockCanteenDatabase()
