"""Domain model for the order processing API."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


# Valid state transitions - prevents e.g. a DELIVERED order from being marked PENDING again.
VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


@dataclass
class OrderItem:
    sku: str
    quantity: int
    unit_price: float


@dataclass
class Order:
    customer_id: str
    items: list[OrderItem]
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderStatus = OrderStatus.PENDING
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "orderId": self.order_id,
            "customerId": self.customer_id,
            "items": [{"sku": i.sku, "quantity": i.quantity, "unitPrice": i.unit_price} for i in self.items],
            "status": self.status.value,
            "subtotal": self.subtotal,
            "tax": self.tax,
            "total": self.total,
            "createdAt": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Order":
        items = [OrderItem(sku=i["sku"], quantity=i["quantity"], unit_price=i["unitPrice"]) for i in data["items"]]
        return Order(
            order_id=data["orderId"],
            customer_id=data["customerId"],
            items=items,
            status=OrderStatus(data["status"]),
            subtotal=data["subtotal"],
            tax=data["tax"],
            total=data["total"],
            created_at=data["createdAt"],
        )
