"""GET /customers/{customerId}/orders - lists all orders for a customer."""

from __future__ import annotations

from src.handlers.common import get_default_repository, handle_service_errors, json_response
from src.repositories.order_repository import BaseOrderRepository
from src.services.order_service import OrderService


@handle_service_errors
def handle(event: dict, repository: BaseOrderRepository) -> dict:
    customer_id = event["pathParameters"]["customerId"]

    service = OrderService(repository)
    orders = service.list_orders_for_customer(customer_id)
    return json_response(200, {"orders": [o.to_dict() for o in orders], "count": len(orders)})


def lambda_handler(event: dict, context) -> dict:
    return handle(event, get_default_repository())
