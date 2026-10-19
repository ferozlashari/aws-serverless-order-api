"""PATCH /orders/{orderId}/status - transitions an order to a new status."""

from __future__ import annotations

import json

from src.handlers.common import get_default_repository, handle_service_errors, json_response
from src.repositories.order_repository import BaseOrderRepository
from src.services.order_service import OrderService


@handle_service_errors
def handle(event: dict, repository: BaseOrderRepository) -> dict:
    order_id = event["pathParameters"]["orderId"]
    body = json.loads(event.get("body") or "{}")
    new_status = body["status"]

    service = OrderService(repository)
    order = service.update_status(order_id, new_status)
    return json_response(200, order.to_dict())


def lambda_handler(event: dict, context) -> dict:
    return handle(event, get_default_repository())
