# Evidence of Correctness

## 1. No double-counting under retries

Test: `tests/test_metering_idempotency.py`

```
$ uv run pytest tests/test_metering_idempotency.py -v

============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /path/to/Usage-Metering-Billing-Service
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
collected 1 item

tests/test_metering_idempotency.py::test_record_usage_idempotency PASSED [100%]

=============================== 1 passed in 0.05s ===============================
```

Manual proof — same request sent twice with the same Idempotency-Key, against a live server:

```
$ curl -i -X POST localhost:8424/usage/record \
    -H "Content-Type: application/json" -H "Idempotency-Key: demo-1" \
    -d '{"tenant_id":"acme","event_type":"api_call","quantity":1,"idempotency_key":"demo-1"}'

HTTP/1.1 200 OK
content-type: application/json

{"id":1,"tenant_id":"acme","event_type":"api_call","quantity":1,"metadata":null,
 "idempotency_key":"demo-1","created_at":"2026-09-02T02:59:37.161670"}

$ curl -i -X POST localhost:8424/usage/record \
    -H "Content-Type: application/json" -H "Idempotency-Key: demo-1" \
    -d '{"tenant_id":"acme","event_type":"api_call","quantity":1,"idempotency_key":"demo-1"}'

HTTP/1.1 200 OK
content-type: application/json

{"id":1,"tenant_id":"acme","event_type":"api_call","quantity":1,"metadata":null,
 "idempotency_key":"demo-1","created_at":"2026-09-02T02:59:37.161670"}
```

Identical `id` in both responses (`1`) — no second row was created. Confirmed directly against the database:

```
$ python -c "
from db.session import SessionLocal
from db.models import UsageEvent
db = SessionLocal()
print(db.query(UsageEvent).filter_by(idempotency_key='demo-1').count())
"
1
```

## 2. Correct cost totals (incl. AI token pricing)

Test: `tests/test_cost_calculation.py`

Hand-computed expectation:
```
cached_input_tokens:   1,000 * 3 microcents/token   =   3,000 microcents
reasoning_tokens:        500 * 150 microcents/token =  75,000 microcents
output_tokens:         2,000 * 150 microcents/token = 300,000 microcents
-------------------------------------------------------------
total (micro-cents) = 378,000 microcents  ->  378,000 / 10,000 = 37.8 -> 38 cents (ceiling)
```

Reproduced directly against `CostService.rollup()`:

```
$ python -c "
... (seed acme with 1000 cached_input_tokens, 500 reasoning_tokens, 2000 output_tokens) ...
result = CostService(db).rollup(tenant_id='acme', start_time=..., end_time=...)
print(result['total_microcents'], result['total_cents'])
"
378000 38
```

Test output:
```
$ uv run pytest tests/test_cost_calculation.py -v

============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /path/to/Usage-Metering-Billing-Service
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
collected 1 item

tests/test_cost_calculation.py::test_cost_service_rollup_aggregation PASSED [100%]

=============================== 1 passed in 0.04s ===============================
```

The test now asserts on `result["total_microcents"]` / `result["total_cents"]` directly (78,000 / 8 for
that test's own fixture numbers), not just the per-event-type quantity breakdown — a total-accumulation
bug was found and fixed during this pass precisely because the total wasn't being checked; see BUILDLOG.md.

## 3. Stripe webhook security

Test: `tests/test_webhooks.py` — 6 tests covering signature verification, dedupe, and state sync for all
three handled event types.

```
$ uv run pytest tests/test_webhooks.py -v

============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /path/to/Usage-Metering-Billing-Service
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
collected 6 items

tests/test_webhooks.py::test_valid_signature_is_processed_and_syncs_tenant PASSED       [ 16%]
tests/test_webhooks.py::test_forged_signature_is_rejected_with_400_and_changes_nothing PASSED [ 33%]
tests/test_webhooks.py::test_missing_signature_header_is_rejected_with_400 PASSED       [ 50%]
tests/test_webhooks.py::test_replayed_event_is_processed_once PASSED                    [ 66%]
tests/test_webhooks.py::test_subscription_updated_syncs_status_and_period PASSED        [ 83%]
tests/test_webhooks.py::test_subscription_deleted_marks_canceled PASSED                 [100%]

=============================== 6 passed in 0.38s ===============================
```

### (a) Legitimate signed event processed

```
$ curl -i -X POST http://localhost:8421/webhooks/stripe \
    -H "Content-Type: application/json" \
    -H "Stripe-Signature: t=1788292254,v1=afd536fed2d12454583b53e5962ef90e637f862717dc0c64067c27de650f6563" \
    --data-binary @checkout_session_completed.json

HTTP/1.1 200 OK
content-type: application/json

{"status":"success","event_id":"evt_evidence_checkout_1"}
```

### (b) Forged signature

```
$ curl -i -X POST http://localhost:8421/webhooks/stripe \
    -H "Content-Type: application/json" \
    -H "Stripe-Signature: t=12345,v1=invalid_fake_signature_hash" \
    -d '{"id": "evt_forged_123", "type": "checkout.session.completed"}'

HTTP/1.1 400 Bad Request
content-type: application/json

{"detail":"Invalid webhook signature: No signatures found matching the expected signature for payload"}
```

### (c) Replay of the same event id

```
$ curl -i -X POST http://localhost:8421/webhooks/stripe \
    -H "Content-Type: application/json" \
    -H "Stripe-Signature: t=1788292254,v1=afd536fed2d12454583b53e5962ef90e637f862717dc0c64067c27de650f6563" \
    --data-binary @checkout_session_completed.json

HTTP/1.1 200 OK
content-type: application/json

{"status":"ignored","reason":"duplicate event"}
```

### (d) State actually synced, not just acknowledged

A `checkout.session.completed` followed by a `customer.subscription.updated` for the same tenant, then
checked directly against the database:

```
$ curl -i -X POST http://localhost:8421/webhooks/stripe ... (customer.subscription.updated) ...
HTTP/1.1 200 OK
{"status":"success","event_id":"evt_evidence_sub_updated_1"}

$ python -c "
from db.session import SessionLocal
from db.models import Tenant, Subscription, WebhookEvent
db = SessionLocal()
t = db.query(Tenant).filter_by(id='acme').first()
print(t.stripe_customer_id, t.status)
sub = db.query(Subscription).filter_by(stripe_subscription_id='sub_evidence_acme').first()
print(sub.status)
print(db.query(WebhookEvent).count())
"
cus_evidence_acme TenantStatus.ACTIVE
SubscriptionStatus.ACTIVE
2
```

Two distinct events recorded (no duplicate from the replay in (c)); tenant and subscription rows reflect
the webhook payloads, not just a 200 response.

## Full test suite

```
$ uv run pytest -v

============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /path/to/Usage-Metering-Billing-Service
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
collected 13 items

tests/test_cost_calculation.py::test_cost_service_rollup_aggregation PASSED             [  7%]
tests/test_metering_idempotency.py::test_record_usage_idempotency PASSED                [ 15%]
tests/test_quota.py::test_quota_under_limit_allowed PASSED                              [ 23%]
tests/test_quota.py::test_quota_at_limit_rejected_with_429 PASSED                       [ 30%]
tests/test_quota.py::test_quota_nonexistent_tenant_raises_404 PASSED                    [ 38%]
tests/test_quota.py::test_quota_past_due_tenant_raises_402 PASSED                       [ 46%]
tests/test_tenant_isolation.py::test_tenant_data_isolation PASSED                       [ 53%]
tests/test_webhooks.py::test_valid_signature_is_processed_and_syncs_tenant PASSED       [ 61%]
tests/test_webhooks.py::test_forged_signature_is_rejected_with_400_and_changes_nothing PASSED [ 69%]
tests/test_webhooks.py::test_missing_signature_header_is_rejected_with_400 PASSED       [ 76%]
tests/test_webhooks.py::test_replayed_event_is_processed_once PASSED                    [ 84%]
tests/test_webhooks.py::test_subscription_updated_syncs_status_and_period PASSED        [ 92%]
tests/test_webhooks.py::test_subscription_deleted_marks_canceled PASSED                 [100%]

======================== 13 passed, 1 warning in 0.65s =========================
```

(The one warning is `StarletteDeprecationWarning` about `httpx` vs `httpx2` in `starlette.testclient` —
a dependency-level notice, not a test failure.)
