# AWS Serverless Order Processing API

A REST API for order management — create orders, track status through a validated lifecycle, list by customer — built on **API Gateway + Lambda + DynamoDB**, defined as Infrastructure-as-Code with **AWS SAM**.

## This one is more thoroughly verified than "no AWS = no testing"

Lambda handlers are just Python functions: `def handler(event, context)`. The only reason they normally can't be tested without AWS is that they usually instantiate a DynamoDB client directly. This project avoids that with **dependency injection**: every handler has a testable `handle(event, repository)` core and a thin `lambda_handler(event, context)` wrapper that supplies the real DynamoDB repository. Tests call `handle()` directly with an `InMemoryOrderRepository` — so the **entire request path** (event parsing, validation, business logic, state machine, error → HTTP status mapping, response formatting) is genuinely exercised, with zero AWS credentials, network access, or `boto3` calls.

**25/25 tests passing**, run for real in this environment — including a full order lifecycle test (PENDING → CONFIRMED → SHIPPED → DELIVERED → verified-terminal).

## Architecture

```
src/
├── models/order.py              Order, OrderItem, OrderStatus + valid state transition map
├── services/
│   ├── pricing.py                  Subtotal/tax/total calculation (regional tax rates)
│   └── order_service.py             Business logic: create/get/list/update-status, validation
├── repositories/order_repository.py  Abstract interface + InMemory (tested) + DynamoDB (production, lazy boto3 import)
└── handlers/
    ├── common.py                     Shared response formatting + error→HTTP-status mapping
    ├── create_order.py                 POST /orders
    ├── get_order.py                     GET /orders/{orderId}
    ├── list_orders.py                    GET /customers/{customerId}/orders
    └── update_order_status.py             PATCH /orders/{orderId}/status
infrastructure/template.yaml      AWS SAM: API Gateway + 4 Lambdas + DynamoDB table w/ GSI
tests/test_all.py                  25 tests - the full request flow, no AWS needed
```

## The order status state machine

Orders can't jump between arbitrary states — `PENDING → CONFIRMED → SHIPPED → DELIVERED` is the happy path, `PENDING`/`CONFIRMED` can be `CANCELLED`, but `DELIVERED` and `CANCELLED` are terminal. Attempting an invalid transition (e.g. un-cancelling a `DELIVERED` order) returns `409 Conflict`, not a silent no-op or a crash — verified in tests.

## Setup & Deploy (requires an AWS account)

```bash
# Install AWS SAM CLI (this sandbox has no network - see below)
pip install aws-sam-cli

sam build
sam deploy --guided   # first time: creates the stack, asks for region/stack name
```

This sandbox couldn't reach PyPI or AWS to actually run `sam build`/`sam deploy` (no network access, no AWS credentials) — the template is written correctly against current SAM syntax but deploy it yourself to confirm, and paste any errors back for a fix.

### Example usage once deployed

```bash
curl -X POST https://{api-url}/prod/orders \
  -H "Content-Type: application/json" \
  -d '{"customerId": "cust-123", "items": [{"sku": "WIDGET-1", "quantity": 2, "unitPrice": 25.0}], "region": "US-CA"}'

curl https://{api-url}/prod/orders/{orderId}

curl -X PATCH https://{api-url}/prod/orders/{orderId}/status \
  -H "Content-Type: application/json" -d '{"status": "CONFIRMED"}'
```

## Testing

```bash
python3 tests/test_all.py
```

25 tests: pricing (regional tax rates, unknown-region fallback), all 4 handlers' happy paths and error paths (missing fields, negative quantities, malformed JSON, nonexistent orders), and the full order lifecycle state machine including the terminal-state guarantee.

## Known limitations / next steps

- No authentication/authorization (API Gateway would need a Cognito authorizer or API keys before production use).
- No idempotency key support on `POST /orders` — a retried request currently creates a duplicate order.
- `DynamoDBOrderRepository.list_by_customer` assumes a `customerId-index` GSI exists (defined in the SAM template) — don't forget it if you hand-roll the table instead of using the template.

## Tech stack

Python · AWS Lambda · API Gateway · DynamoDB · AWS SAM
