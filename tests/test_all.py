"""
Test suite for the order API. Calls Lambda handlers directly with
API-Gateway-shaped event dicts and an injected InMemoryOrderRepository -
no AWS credentials, network, or boto3 required. This exercises the exact
same code path AWS would invoke in production (event parsing, service
logic, error handling, response formatting) end-to-end.

Run with: python3 tests/test_all.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.repositories.order_repository import InMemoryOrderRepository
from src.handlers import create_order, get_order, list_orders, update_order_status
from src.services.pricing import calculate_total
from src.models.order import OrderItem

passed = 0
failed = 0


def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}")


def create_test_order(repo, customer_id="cust-1", items=None, region="US-OR"):
    items = items or [{"sku": "SKU-1", "quantity": 1, "unitPrice": 10.0}]
    event = {"body": json.dumps({"customerId": customer_id, "items": items, "region": region})}
    return create_order.handle(event, repo)


print("== pricing ==")
items = [OrderItem("A", 2, 25.0), OrderItem("B", 1, 50.0)]
subtotal, tax, total = calculate_total(items, "US-CA")
check("subtotal sums quantity * unit_price across items", subtotal == 100.0)
check("tax applies the correct regional rate", tax == 7.25)
check("total is subtotal + tax", total == 107.25)

subtotal, tax, total = calculate_total(items, "US-OR")
check("Oregon has zero sales tax", tax == 0.0)

subtotal, tax, total = calculate_total(items, "US-UNKNOWN")
check("unknown region falls back to default tax rate rather than erroring", tax == round(100.0 * 0.05, 2))

print("== create_order handler ==")
repo = InMemoryOrderRepository()
response = create_test_order(repo, items=[{"sku": "X", "quantity": 2, "unitPrice": 30.0}], region="US-NY")
body = json.loads(response["body"])
check("returns 201 on success", response["statusCode"] == 201)
check("computes correct total with regional tax", body["total"] == 64.8)  # 60 + 8% NY tax
check("new order starts in PENDING status", body["status"] == "PENDING")
check("response includes a generated orderId", "orderId" in body and len(body["orderId"]) > 0)

response = create_order.handle({"body": json.dumps({"items": [{"sku": "X", "quantity": 1, "unitPrice": 1}]})}, repo)
check("missing customerId returns 400", response["statusCode"] == 400)

response = create_order.handle({"body": json.dumps({"customerId": "c1", "items": []})}, repo)
check("empty items list returns 400", response["statusCode"] == 400)

response = create_order.handle(
    {"body": json.dumps({"customerId": "c1", "items": [{"sku": "X", "quantity": -1, "unitPrice": 10}]})}, repo
)
check("negative quantity returns 400", response["statusCode"] == 400)

response = create_order.handle({"body": "not valid json"}, repo)
check("malformed JSON body returns 400, not a 500 crash", response["statusCode"] == 400)

print("== get_order handler ==")
repo = InMemoryOrderRepository()
create_response = create_test_order(repo)
order_id = json.loads(create_response["body"])["orderId"]

response = get_order.handle({"pathParameters": {"orderId": order_id}}, repo)
check("fetches an existing order with 200", response["statusCode"] == 200)

response = get_order.handle({"pathParameters": {"orderId": "nonexistent-id"}}, repo)
check("fetching a nonexistent order returns 404, not a crash", response["statusCode"] == 404)

print("== list_orders handler ==")
repo = InMemoryOrderRepository()
create_test_order(repo, customer_id="cust-A")
create_test_order(repo, customer_id="cust-A")
create_test_order(repo, customer_id="cust-B")

response = list_orders.handle({"pathParameters": {"customerId": "cust-A"}}, repo)
body = json.loads(response["body"])
check("lists only orders for the requested customer", body["count"] == 2)

response = list_orders.handle({"pathParameters": {"customerId": "cust-nonexistent"}}, repo)
check("customer with no orders returns an empty list, not an error", json.loads(response["body"])["count"] == 0)

print("== update_order_status handler (state machine) ==")
repo = InMemoryOrderRepository()
create_response = create_test_order(repo)
order_id = json.loads(create_response["body"])["orderId"]

response = update_order_status.handle(
    {"pathParameters": {"orderId": order_id}, "body": json.dumps({"status": "CONFIRMED"})}, repo
)
check("valid transition PENDING -> CONFIRMED succeeds", response["statusCode"] == 200)

response = update_order_status.handle(
    {"pathParameters": {"orderId": order_id}, "body": json.dumps({"status": "PENDING"})}, repo
)
check("invalid transition CONFIRMED -> PENDING returns 409, not silently allowed", response["statusCode"] == 409)

response = update_order_status.handle(
    {"pathParameters": {"orderId": order_id}, "body": json.dumps({"status": "NOT_A_REAL_STATUS"})}, repo
)
check("unrecognized status value returns 400", response["statusCode"] == 400)

response = update_order_status.handle(
    {"pathParameters": {"orderId": "nonexistent"}, "body": json.dumps({"status": "CONFIRMED"})}, repo
)
check("updating a nonexistent order returns 404", response["statusCode"] == 404)

# Full lifecycle: PENDING -> CONFIRMED -> SHIPPED -> DELIVERED, then verify DELIVERED is terminal.
repo = InMemoryOrderRepository()
order_id = json.loads(create_test_order(repo)["body"])["orderId"]
for status in ["CONFIRMED", "SHIPPED", "DELIVERED"]:
    response = update_order_status.handle(
        {"pathParameters": {"orderId": order_id}, "body": json.dumps({"status": status})}, repo
    )
    check(f"lifecycle step to {status} succeeds", response["statusCode"] == 200)

response = update_order_status.handle(
    {"pathParameters": {"orderId": order_id}, "body": json.dumps({"status": "CANCELLED"})}, repo
)
check("DELIVERED is a terminal state - cannot cancel after delivery", response["statusCode"] == 409)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
