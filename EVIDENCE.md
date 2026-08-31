# Evidence of Correctness

Fill each section in as you implement it — this file is graded evidence, not
just documentation. Paste real command output / transcripts, not summaries.

## 1. No double-counting under retries

Test: `tests/test_metering_idempotency.py`

```
$ uv run pytest tests/test_metering_idempotency.py -v

=============================================================== test session starts ===============================================================
platform linux -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0 -- /mnt/Projects/Projects/Usage-Metering-Billing-Service/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /mnt/Projects/Projects/Usage-Metering-Billing-Service
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 1 item                                                                                                                                  

tests/test_metering_idempotency.py::test_record_usage_idempotency PASSED                                                                    [100%]

================================================================ 1 passed in 0.05s ================================================================

```

Manual proof — same request sent twice with the same Idempotency-Key:

```
$ curl -X POST localhost:8000/usage/record -H "Idempotency-Key: demo-1" -d '{...}'
# paste response 1

$ curl -X POST localhost:8000/usage/record -H "Idempotency-Key: demo-1" -d '{...}'
# paste response 2 — identical, and only ONE row in usage_events for this key

$ sqlite3 billing.db "select count(*) from usage_events where idempotency_key='demo-1';"
# expect: 1
```

## 2. Correct cost totals (incl. AI token pricing)

Test: `tests/test_cost_calculation.py`

Hand-computed expectation:
```
input_tokens:        <n> * PRICE_INPUT_TOKEN_MICROCENTS         = <x>
cached_input_tokens:   1,000 * 3 microcents/token   =   3,000 microcents
reasoning_tokens:        500 * 150 microcents/token =  75,000 microcents
output_tokens:         2,000 * 150 microcents/token = 300,000 microcents
-------------------------------------------------------------
total (micro-cents) = 378,000 microcents  ->  378,000 / 10,000 = 37.8 (38 cents rounded)
```

Test output:
```
$ uv run pytest tests/test_cost_calculation.py -v

=============================================================== test session starts ===============================================================
platform linux -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0 -- /mnt/Projects/Projects/Usage-Metering-Billing-Service/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /mnt/Projects/Projects/Usage-Metering-Billing-Service
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 1 item                                                                                                                                  

tests/test_cost_calculation.py::test_cost_service_rollup_aggregation PASSED                                                                 [100%]

================================================================ 1 passed in 0.04s ================================================================
```

## 3. Stripe webhook security

### Legitimate Signed Event Processed

```
$ stripe trigger checkout.session.completed
Running in Test mode sandbox · sandbox (acct_1U920E4JOVZvbHpt)
Setting up fixture for: product
Running fixture for: product
Setting up fixture for: price
Running fixture for: price
Setting up fixture for: checkout_session
Running fixture for: checkout_session
Setting up fixture for: payment_page
Running fixture for: payment_page
Setting up fixture for: payment_method
Running fixture for: payment_method
Setting up fixture for: payment_page_confirm
Running fixture for: payment_page_confirm
Trigger succeeded! Check dashboard for event details.
```

### Forged signature:

```
$ curl -i -X POST http://localhost:8000/webhooks/stripe
-H "Content-Type: application/json"
-H "Stripe-Signature: t=12345,v1=invalid_fake_signature_hash"
-d '{"id": "evt_forged_123", "type": "checkout.session.completed"}'

HTTP/1.1 400 Bad Request
date: Mon, 31 Aug 2026 15:12:18 GMT
server: uvicorn
content-length: 103
content-type: application/json

{"detail": "Invalid webhook signature: No signatures found matching the expected signature for payload"}
```

### Replay of the same event id:

```
$ stripe events resend evt_...
Running in Test mode sandbox · sandbox (acct_1U920E4JOVZvbHpt)
{
"id": "evt_3UAWrG4JOVZvbHpt0tYVyvLz",
"object": "event",
"api_version": "2026-08-26.dahlia",
"created": 1788189053,
"type": "charge.updated"
}
```
