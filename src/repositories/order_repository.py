"""
Order repository. The abstract interface lets handlers/services be tested
with InMemoryOrderRepository (no AWS needed) while production code uses
DynamoDBOrderRepository (boto3, lazy-imported so this module itself doesn't
require boto3 to be installed just to run tests against the in-memory version).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.models.order import Order


class OrderNotFoundError(Exception):
    pass


class BaseOrderRepository(ABC):
    @abstractmethod
    def save(self, order: Order) -> None: ...

    @abstractmethod
    def get(self, order_id: str) -> Order: ...

    @abstractmethod
    def list_by_customer(self, customer_id: str) -> list[Order]: ...


class InMemoryOrderRepository(BaseOrderRepository):
    """Used in tests and local development - no AWS credentials or network required."""

    def __init__(self):
        self._orders: dict[str, Order] = {}

    def save(self, order: Order) -> None:
        self._orders[order.order_id] = order

    def get(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(f"Order '{order_id}' not found")
        return order

    def list_by_customer(self, customer_id: str) -> list[Order]:
        return [o for o in self._orders.values() if o.customer_id == customer_id]


class DynamoDBOrderRepository(BaseOrderRepository):
    """
    Production repository backed by DynamoDB. Table schema:
      Partition key: orderId (String)
      GSI: customerId-index, partition key customerId (String)
    Requires `boto3` and AWS credentials/network - not available in this
    sandbox (see README), so this class is syntax-checked but not executed here.
    """

    def __init__(self, table_name: str):
        import boto3  # lazy import - only needed when this class is actually used

        self._table = boto3.resource("dynamodb").Table(table_name)

    def save(self, order: Order) -> None:
        self._table.put_item(Item=order.to_dict())

    def get(self, order_id: str) -> Order:
        response = self._table.get_item(Key={"orderId": order_id})
        item = response.get("Item")
        if item is None:
            raise OrderNotFoundError(f"Order '{order_id}' not found")
        return Order.from_dict(item)

    def list_by_customer(self, customer_id: str) -> list[Order]:
        response = self._table.query(
            IndexName="customerId-index",
            KeyConditionExpression="customerId = :cid",
            ExpressionAttributeValues={":cid": customer_id},
        )
        return [Order.from_dict(item) for item in response.get("Items", [])]
