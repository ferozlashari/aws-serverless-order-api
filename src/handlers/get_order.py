"""GET /orders/{orderId} - fetches a single order."""

from __future__ import annotations

from src.handlers.common import get_default_repository, handle_service_errors, json_response
from src.repositories.order_repository import BaseOrderRepository
from src.services.order_service import OrderService


@handle_service_errors
def handle(event: dict, repository: BaseOrderRepository) -> dict:
    order_id = event["pathParameters"]["orderId"]

    service = OrderService(repository)
    order = service.get_order(order_id)
    return json_response(200, order.to_dict())


def lambda_handler(event: dict, context) -> dict:
    return handle(event, get_default_repository())
