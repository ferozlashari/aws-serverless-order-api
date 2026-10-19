"""
POST /orders - creates a new order.

Deployed as a Lambda behind API Gateway (see infrastructure/template.yaml).
`lambda_handler` is the entry point AWS calls; `handle` is the testable core
that accepts an injected repository so tests never touch DynamoDB/boto3.
"""

from __future__ import annotations

import json

from src.handlers.common import get_default_repository, handle_service_errors, json_response
from src.repositories.order_repository import BaseOrderRepository
from src.services.order_service import OrderService


@handle_service_errors
def handle(event: dict, repository: BaseOrderRepository) -> dict:
    body = json.loads(event.get("body") or "{}")

    service = OrderService(repository)
    order = service.create_order(
        customer_id=body.get("customerId"),
        items=body.get("items", []),
        region=body.get("region", "US-OR"),
    )
    return json_response(201, order.to_dict())


def lambda_handler(event: dict, context) -> dict:
    return handle(event, get_default_repository())
