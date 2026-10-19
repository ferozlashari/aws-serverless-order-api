"""Shared utilities for Lambda handlers: JSON response formatting and repository wiring."""

from __future__ import annotations

import json
import os

from src.repositories.order_repository import BaseOrderRepository
from src.services.order_service import InvalidTransitionError, OrderService, ValidationError
from src.repositories.order_repository import OrderNotFoundError


def json_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def get_default_repository() -> BaseOrderRepository:
    """
    Production repository, wired from the ORDERS_TABLE_NAME env var (set in
    the SAM/Terraform template). Handlers accept an optional `repository`
    parameter so tests can inject InMemoryOrderRepository instead of calling
    this function at all.
    """
    from src.repositories.order_repository import DynamoDBOrderRepository

    table_name = os.environ["ORDERS_TABLE_NAME"]
    return DynamoDBOrderRepository(table_name)


def handle_service_errors(fn):
    """Decorator: converts service-layer exceptions into proper HTTP error responses."""

    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValidationError as e:
            return json_response(400, {"error": "validation_error", "message": str(e)})
        except OrderNotFoundError as e:
            return json_response(404, {"error": "not_found", "message": str(e)})
        except InvalidTransitionError as e:
            return json_response(409, {"error": "invalid_transition", "message": str(e)})
        except (KeyError, json.JSONDecodeError) as e:
            return json_response(400, {"error": "bad_request", "message": f"Malformed request: {e}"})

    return wrapper
