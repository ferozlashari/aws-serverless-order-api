"""
Order service: the business logic layer, independent of both the Lambda
runtime and any specific database. Takes a repository (interface) as a
constructor argument, so it can be tested with InMemoryOrderRepository and
used in production with DynamoDBOrderRepository - the logic itself doesn't change.
"""

from __future__ import annotations

from src.models.order import Order, OrderItem, OrderStatus, VALID_TRANSITIONS
from src.repositories.order_repository import BaseOrderRepository
from src.services.pricing import calculate_total


class ValidationError(Exception):
    pass


class InvalidTransitionError(Exception):
    pass


class OrderService:
    def __init__(self, repository: BaseOrderRepository):
        self.repository = repository

    def create_order(self, customer_id: str, items: list[dict], region: str = "US-OR") -> Order:
        if not customer_id:
            raise ValidationError("customerId is required")
        if not items:
            raise ValidationError("At least one item is required")

        order_items = []
        for raw in items:
            if raw.get("quantity", 0) <= 0:
                raise ValidationError(f"Item '{raw.get('sku')}' must have a positive quantity")
            if raw.get("unitPrice", 0) < 0:
                raise ValidationError(f"Item '{raw.get('sku')}' cannot have a negative price")
            order_items.append(OrderItem(sku=raw["sku"], quantity=raw["quantity"], unit_price=raw["unitPrice"]))

        subtotal, tax, total = calculate_total(order_items, region)

        order = Order(customer_id=customer_id, items=order_items, subtotal=subtotal, tax=tax, total=total)
        self.repository.save(order)
        return order

    def get_order(self, order_id: str) -> Order:
        return self.repository.get(order_id)

    def list_orders_for_customer(self, customer_id: str) -> list[Order]:
        return self.repository.list_by_customer(customer_id)

    def update_status(self, order_id: str, new_status: str) -> Order:
        order = self.repository.get(order_id)

        try:
            new_status_enum = OrderStatus(new_status)
        except ValueError:
            raise ValidationError(f"Invalid status '{new_status}'")

        allowed = VALID_TRANSITIONS.get(order.status, set())
        if new_status_enum not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition order from {order.status.value} to {new_status_enum.value}"
            )

        order.status = new_status_enum
        self.repository.save(order)
        return order
