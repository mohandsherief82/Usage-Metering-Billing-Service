# Evidence of Correctness

Fill each section in as you implement it — this file is graded evidence, not
just documentation. Paste real command output / transcripts, not summaries.

## 1. No double-counting under retries

Test: `tests/test_metering_idempotency.py`

```
$ uv run pytest tests/test_metering_idempotency.py -v
# paste output here
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
cached_input_tokens:  <n> * PRICE_CACHED_INPUT_TOKEN_MICROCENTS  = <x>
reasoning_tokens:     <n> * PRICE_REASONING_TOKEN_MICROCENTS     = <x>
output_tokens:        <n> * PRICE_OUTPUT_TOKEN_MICROCENTS        = <x>
-------------------------------------------------------------
total (micro-cents) = <sum>  ->  <sum / MICROCENTS_PER_CENT> cents
```

```
$ uv run pytest tests/test_cost_calculation.py -v
# paste output here — should match hand-computed total exactly
```

## 3. Stripe webhook security

Test: `tests/test_webhooks.py`

```
$ stripe trigger checkout.session.completed
# paste stripe CLI + server log showing: signature verified, event processed, tenant updated

# forged signature:
$ curl -X POST localhost:8000/webhooks/stripe -H "Stripe-Signature: bad" -d '{...}'
# expect: 400

# replay of the same event id:
$ stripe events resend evt_...
# paste log showing it was recognized as already-processed and ignored (no duplicate side effect)
```
