# Build Log — AI usage, honestly

Required by the brief (Section 3 & 10): AI-assisted building is encouraged, but this log
has to stay honest about where it helped, where it was wrong, and what got changed. The
bar the brief sets: you must be able to explain any 2–3 lines of your code that an
evaluator points at. "The AI wrote it" is not an answer — this file is where you show the
work of actually owning the code.

Update this **as you build**, not retroactively at submission time — specifics fade fast.
Vague entries ("AI helped with the webhook handler") aren't useful; be concrete about what
was wrong and what you changed, e.g. "AI's first draft of verify_and_parse_webhook read
the body via request.json() before verifying the signature — that reserializes the payload
and breaks signature verification. Fixed by reading request.body() raw and passing those
exact bytes to stripe.Webhook.construct_event."

## Format

### <date> — <what you were building>
- **Where AI helped**: ... 
- **Where it was wrong / had to be corrected**: ...
- **What I changed and why**: ... 

---

## Entries

### 2026-08-28 — Project scaffolding, architecture, TUI
- **Where AI helped**: generated the initial folder structure, `pyproject.toml`, D2
  architecture diagram, GUIDE.md checklist, and the full Textual TUI (screens, custom
  widgets, theme, async data layer with live/demo fallback).
- **Where it was wrong / had to be corrected**: the model used has created an extremely complex folder structure. Also, the run command generated to run the TUI wasn't correct.
- **What I changed and why**: I have simplified the folder structure to a more organized structure for easier traversal and updated the model's understanding of the hierarchy. The run command of the TUI was running a Welcome page to the textual framework, therefore I had to update it and use the correct command.

### Data model schema
- **Where AI helped**: Code generation
- **Where it was wrong / had to be corrected**: nothing. 
- **What I changed and why**: after reviewing the generated artificats, I have found everything defined perfectly according to the design I choose and available in the GUIDE.md file. 

### <date> — Webhook routing, cost totals, metadata persistence (verification pass)
- **Where AI helped**: Wrote `tests/test_webhooks.py` (6 tests: valid signature + full
  state-sync, forged signature → 400, missing signature → 400, replay → processed once,
  subscription updated/deleted sync). While getting it to actually pass against the real
  app (not just compile), found and fixed four bugs that had slipped past the existing
  test suite and were undetected in the checked-off GUIDE.md.
- **Where it was wrong / had to be corrected**:
  1. `api/webhooks.py` had two identically-routed `@webhook_router.post("/stripe", ...)`
     handlers. FastAPI registered both; the incomplete first one always won, so the real
     one (which synced Tenant/Subscription state) was permanently dead code. Proved live:
     a valid signed `checkout.session.completed` returned `200 success` but never touched
     the tenant.
  2. `CostService.rollup()`'s `total_cents`/`total_microcents` were hardcoded to always
     return 0 — a line inside the accumulation loop was overwriting the running total
     instead of adding to it. Reproduced EVIDENCE.md's own hand-computed scenario
     (1,000 cached input + 500 reasoning + 2,000 output tokens) and got `0`, not `378,000`/
     `38` as documented. The existing test only checked the per-type breakdown, never the
     total — exactly how this slipped through.
  3. `MeterService.record()` passed `metadata=metadata` into the `UsageEvent` constructor.
     The real mapped attribute is `meta` (SQLAlchemy reserves `metadata` for its own
     schema registry) — the kwarg silently shadowed an unrelated class attribute instead
     of raising an error, so metadata was always discarded.
  4. Same collision, opposite direction: `UsageRecordResponse`'s `meta` field with
     `alias="metadata"` caused Pydantic's `from_attributes` lookup to resolve
     `event.metadata` (SQLAlchemy's registry object) instead of `event.meta`, crashing
     `POST /usage/record` with a raw 500 on response serialization.
  5. `TestClient` + in-memory SQLite needed `poolclass=StaticPool` in `conftest.py` — each
     new connection was otherwise getting its own separate `:memory:` database, so tables
     "didn't exist" from the request-handling thread's point of view.
- **What I changed and why**: Removed the dead webhook handler, keeping the complete one;
  fixed it to convert the Stripe event to a plain dict once at the router boundary
  (`stripe.StripeObject` doesn't support `.get()` like a dict in this SDK version — every
  `.get()` call throughout the handler logic would otherwise raise `AttributeError`).
  Fixed the cost accumulation loop. Changed `metadata=metadata` to `meta=metadata` in
  `MeterService.record()`. Rewrote `UsageRecordResponse` to a plain `metadata` field
  constructed explicitly in the route handler rather than relying on ORM auto-mapping.
  Added `StaticPool` to the test fixture. Strengthened `test_cost_calculation.py` to
  assert on `total_cents`/`total_microcents` directly, not just the breakdown, so bug #2
  can't silently regress. Rewrote `EVIDENCE.md` with real transcripts from the fixed code
  (live curl requests against a running server, not just pytest output).

### Rate limiting: Retry-After header on 429
- **Where AI helped**: Added a `Retry-After` header to `QuotaService.check_quota()`'s 429
  response, computed as seconds until the tenant's quota resets.
- **Where it was wrong / had to be corrected**: First version compared
  `subscription.current_period_end` (read back from SQLite) against
  `datetime.now(timezone.utc)` and got `TypeError: can't compare offset-naive and
  offset-aware datetimes` — SQLite doesn't reliably round-trip tzinfo through
  `DateTime(timezone=True)`. Also, my first attempt at adding a test for this accidentally
  merged its body into the neighboring `test_quota_nonexistent_tenant_raises_404` test via
  a bad find-and-replace — caught it because the test count didn't match what I expected
  (4 shown instead of 5), split them back into two proper functions.
- **What I changed and why**: If a naive datetime comes back from the DB, treat it as UTC
  (the convention every write already uses) before comparing. Retry-After prefers the
  tenant's actual `Subscription.current_period_end` when one exists (matches real Stripe
  billing periods, which don't align to calendar months); falls back to end-of-calendar-
  month for tenants with no subscription (the Free tier). Added a test asserting the
  header value matches a seeded subscription's period end, not just "some positive
  number", and verified live against a running server (real `429` with a real
  `retry-after: 2465757` header, not just a passing unit test).
