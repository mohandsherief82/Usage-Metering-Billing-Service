# Build Guide — Usage Metering & Billing System

Capstone checklist. Check items off as you go. Each section links resources.

## 0. Environment & Stripe access (Egypt-specific)

Stripe does not let you open a native account from Egypt (not on their supported-country
list). For a **test-mode-only** capstone this is a paperwork problem, not a technical one —
no money moves and no payout/KYC is required to use the API/webhooks/Checkout in test mode.
Two practical routes:

- [X] **Fastest for a capstone**: sign up at https://dashboard.stripe.com/register selecting
      a supported country (e.g. US) as a placeholder business address. You only need the
      account to generate `sk_test_...` / `whsec_...` keys and use Checkout + webhooks in
      test mode — this is standard practice for devs in unsupported countries who are
      learning/prototyping, not processing real payouts.
- [X] If you later want a *real* Egyptian business on Stripe: that requires incorporating in
      a supported country (US LLC, UK Ltd, etc.) — out of scope for this project, just know
      the option exists.
- [X] Install Stripe CLI: https://docs.stripe.com/stripe-cli
- [X] `stripe login`, then `stripe listen --forward-to localhost:8000/webhooks/stripe` — copy
      the `whsec_...` it prints into `.env` as `STRIPE_WEBHOOK_SECRET`.
- [X] Confirm `.env` is git-ignored (`.gitignore` already covers it) and `.env.example` has
      no real secrets.

## 1. Language & tooling decision (done)

- **Language**: Python — chosen over TypeScript specifically for the TUI. **Textual**
  (https://textual.textualize.io) gives CSS-like styling, reactive widgets, live-updating
  tables/sparklines, and a built-in dev console (`textual run --dev`) for hot reload —
  more control over a "fancy" terminal UI than Node TUI libs (ink/blessed/blessed-contrib)
  at comparable effort, and it shares one language/runtime with the FastAPI backend and
  test suite (no context-switching, one dependency graph).
- **Backend**: FastAPI + SQLAlchemy 2.0 (async-capable, typed, plays well with Pydantic
  for the request/response schemas quotas and cost rollups need).
- **Build tool**: `uv` (https://docs.astral.sh/uv/) — `uv sync`, `uv run`, lockfile, fast.
- [X] `uv sync` to create `.venv` and install from `pyproject.toml`.
- [X] `uv run pytest` / `uv run uvicorn billing.main:app --reload` / `uv run textual run src/billing/tui/app.py`.

## 2. Data model

- [X] `Tenant` (id, name, stripe_customer_id, plan_id, status) — implemented in
      `src/db/models.py`. Uses the tenant slug (e.g. `"acme"`) as the primary key
      rather than a surrogate int, since that's the value that actually shows up in API
      paths, idempotency keys, and logs. `plan_id` is a plain column for now — the
      `ForeignKey` constraint gets added once `Plan` exists (next item below), so it isn't
      referencing a table that doesn't exist yet. `status` is a proper enum
      (`active` / `past_due` / `canceled`), not a free-text string.
- [X] `Plan` (id, name, monthly_quota, price_cents, pricing_config — pinned constants)
- [X] `Subscription` (id, tenant_id, stripe_subscription_id, status, current_period_start/end)
- [X] `UsageEvent` (id, tenant_id, event_type, quantity, metadata, **idempotency_key UNIQUE**, created_at)
- [X] `WebhookEvent` (id = stripe event id PRIMARY KEY, type, processed_at) — this table *is*
      your webhook dedupe mechanism.
- [X] Every query scoped by `tenant_id` — no cross-tenant leakage (add a test asserting this).
- [X] Alembic migration for the above: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- [X] All money fields are `Integer` (cents / micro-units) — never `Float`/`Numeric` for
      currency arithmetic. Enforce in `config.py` + code review, not just convention.
- [ ] **DB choice**: the brief's stack table (Section 10) lists Postgres via Docker as the
      primary path, SQLite as the fallback — not the other way around. Default
      `DATABASE_URL` in `.env.example` is SQLite for zero-setup dev, but stand up
      `docker-compose.yml` (see §11) before you're deep into implementation, not as an
      afterthought — Alembic + Postgres-specific `ON CONFLICT` syntax (§3) assumes it.

## 3. Metering (`MeterService.record`)

- [X] `record(tenant_id, event_type, quantity, idempotency_key)`:
      1. `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING RETURNING *` (Postgres) or
         catch the unique-constraint `IntegrityError` and re-fetch the existing row (SQLite).
      2. If a row already existed for that key → return **that** row's result, do **not**
         run quota logic again for a duplicate (the original response already reflected it).
- [X] Idempotency-key pattern reference: https://docs.stripe.com/api/idempotent_requests
      (Stripe's own docs — same pattern, useful even though this isn't a Stripe call).
- [X] **EVIDENCE.md proof**: write a test that calls `record()` twice with the same key
      (simulating a client retry), assert only one `UsageEvent` row exists, and paste the
      test output / a `curl` transcript sending the same `POST /usage/record` body+header
      twice showing identical responses and a single DB row.

## 4. Quotas

- [X] After a usage event is durably recorded, sum the tenant's usage for the current
      billing period and compare to `Plan.monthly_quota`.
- [X] Over limit → return **402 Payment Required** if the plan itself is exhausted/unpaid,
      or **429 Too Many Requests** if it's a rate/quota throttle — pick one convention and
      document it in README (mentor asked for "the correct status codes", so be explicit
      about *which* condition maps to which code).
- [X] Response body always includes a human-readable `message` (e.g. `"tenant acme is at
      1000/1000 API calls for this billing period"`), not just the status code.
- [X] HTTP status code reference: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status

## 5. Cost calculation

- [X] `CostService.rollup(tenant_id, period)` sums `UsageEvent.quantity` by `event_type`
      for the period and multiplies by the pinned per-unit price from `config.py`.
- [X] AI token pricing must separately account for: input tokens, **cached** input tokens
      (usually priced lower), **reasoning/thinking** tokens, and output tokens — model this
      as distinct `event_type`s (`input_tokens`, `cached_input_tokens`, `reasoning_tokens`,
      `output_tokens`) each with its own price-per-unit constant, not one blended rate.
      Reference for the shape of this pricing model: https://docs.anthropic.com/en/docs/about-claude/pricing
      and https://platform.openai.com/docs/pricing (for comparison — pin your *own* made-up
      constants in `config.py`, don't hardcode a live vendor price that will drift).
- [X] All pricing constants live in one place (`src/billing/config.py`) with comments citing
      units (e.g. "cents per 1K tokens"), never inline magic numbers in service code.
- [ ] **EVIDENCE.md proof**: a test with a hand-computed expected total (e.g. 1,000 cached
      input + 500 reasoning + 2,000 output tokens → exact expected cents) asserted against
      `CostService.rollup()`'s output, with the test output pasted in.

## 6. Stripe integration

- [ ] Checkout Session: https://docs.stripe.com/checkout/quickstart — create a Checkout
      Session server-side for a plan's Stripe Price, redirect the client to
      `session.url`, confirm `checkout.session.completed` arrives via webhook.
- [ ] Webhook endpoint: https://docs.stripe.com/webhooks — verify with
      `stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)`; a bad
      signature must raise → return 400.
- [ ] Dedupe using the `WebhookEvent` table: check `event.id` before processing, upsert it
      after — replaying the same event (via `stripe trigger` or CLI replay) must be a no-op.
- [ ] Handle at minimum: `checkout.session.completed`, `customer.subscription.updated`,
      `customer.subscription.deleted` → update `Tenant.plan_id` / `Subscription.status`.
- [ ] Test locally end-to-end with `stripe listen --forward-to localhost:8000/webhooks/stripe`
      and `stripe trigger checkout.session.completed` — no tunnel/public URL needed.
- [ ] **EVIDENCE.md proof**: paste a webhook log showing (a) one legitimate signed event
      processed, (b) a forged/tampered signature rejected with 400, (c) the same event id
      replayed and ignored.

## 7. TUI (Textual)

- [X] `App` with a couple of `Screen`s: live dashboard (per-tenant used/limit/cost table,
      refreshed on a timer via `GET /usage`), tenant list, raw usage-event log/tail.
- [X] Use `DataTable`, `Sparkline`/`ProgressBar` for quota gauges, and CSS
      (`app.css` or inline `DEFAULT_CSS`) for a distinct visual identity — this is the
      "fancy" part, lean into it once the plumbing works.
- [X] Textual docs/tutorial: https://textual.textualize.io/tutorial/
      Widget gallery: https://textual.textualize.io/widget_gallery/

## 8. Tests

- [X] `tests/test_metering_idempotency.py` — double-submit proof (see §3).
- [ ] `tests/test_quota.py` — under-limit allowed, at-limit rejected with correct code+message.
- [X] `tests/test_cost_calculation.py` — hand-computed totals (see §5).
- [ ] `tests/test_webhooks.py` — valid signature accepted, invalid rejected (400), replay ignored.
- [ ] `uv run pytest -v` output captured into EVIDENCE.md alongside the manual transcripts.

## 9. Shared requirements (every capstone must show these)

Section 12 of the brief lists requirements that apply across every FlyRank capstone, not
just this one. Two of them aren't covered by §1–8 above and are easy to miss:

- [ ] **Validation at the boundary** — every API route rejects malformed input with a clean
      4xx (`422`/`400` with a body explaining what's wrong), never a raw `500`. Use Pydantic
      request models for this — a body that fails schema validation should never reach
      service code. Covers e.g. negative `quantity`, missing `idempotency_key`, unknown
      `tenant_id`.
- [ ] **≥1 background job** — some slow/bulk work must run off the request path, with
      retries and a failure alert (even just a log line at ERROR level counts as the
      "alert" for a capstone). The natural fit here is the **reconciliation job** from §11 —
      if you pick that as your one deep-dive stretch goal, it satisfies this requirement too;
      otherwise you need a smaller stand-in (e.g. a periodic job that recomputes cost
      rollups) so this box isn't left unchecked.
- [ ] Secrets clean (env only, never logged) — already covered by §0.
- [ ] Cost tracked per call, attributed, with a budget guard — already covered by §5
      (quota enforcement *is* the budget guard here).
- [ ] Layered architecture (data/logic/HTTP separated) — already the shape of `db/` /
      `services/` / `api/` in the folder structure.
- [ ] Idempotency where it matters — already covered by §3.

## 10. Docs & submission pack (Section 10–11 deliverables)

- [ ] `README.md` — what it is, stack, how to run (`uv sync`, `.env` setup, `stripe listen`,
      `uv run uvicorn ...`, `uv run textual run ...`), API summary.
- [ ] Architecture diagram — `architecture.d2` (already in repo root) →
      `d2 architecture.d2 architecture.svg` (D2 install: https://d2lang.com/tour/install).
- [ ] `EVIDENCE.md` — the three proofs from §3, §5, §6 above, all in one file.
- [ ] `.env.example` present, `.env` git-ignored (both already done).
- [ ] `capstone.yaml` — the manifest the evaluator reads (`run:`, `seed:`, `test:`,
      `base_url:`, endpoints to probe). Stub already created — fill in real values as each
      piece comes online; don't leave placeholder commands in the final submission.
- [ ] `BUILDLOG.md` — your AI-usage log (where AI helped, where it was wrong, what you
      changed). Stub already created — update it *as you build*, not retroactively; you
      won't remember the specifics by submission time.
- [ ] Repo hygiene per Section 11 of the brief: separate public repo from day one, never
      inside a repo with other work, suggested name pattern
      `flyrank-capstone-metering-billing` (lowercase, hyphens), small meaningful commits
      as you go so each phase in §8 is visible in history.

## 11. Nice-to-haves once core is green

A finished core with one polished stretch beats three half-stretches. Pick **one** of the
deep-dive items below and take it all the way — each is a genuine "I went deep" interview
story on its own; three shallow attempts isn't.

- [ ] Rate limiting header hints (`Retry-After` on 429).
- [ ] Seed script (`scripts/seed_db.py`) for demo tenants/plans — stub already created.
- [ ] `docker-compose.yml` for local Postgres — this is the brief's primary DB path (§2
      above), not just a nice-to-have; stand it up early rather than deferring it.

### Pick one deep-dive stretch goal

- [ ] **Overage billing** — allow usage beyond the plan limit instead of hard-rejecting,
      and calculate the additional charges as they accrue (plus a projected end-of-period
      cost based on current pace).
- [ ] **Invoices** — generate a monthly statement per tenant with itemized usage line items
      (mirrors what `CostService.rollup()` already computes, formatted as a real invoice).
- [ ] **Usage alerts** — notify a tenant at 80% and 100% of their quota (log/webhook/email
      stub is fine — the logic of *when* and *exactly once* per threshold is the point).
- [ ] **Proration** — correctly handle a mid-cycle plan upgrade/downgrade: credit the unused
      portion of the old plan, charge the prorated portion of the new one. Genuinely tricky
      — a great "I went deep" story precisely because it's easy to get subtly wrong.
- [ ] **Reconciliation job** — a nightly job comparing your database's view of
      tenants/subscriptions against Stripe's actual state via the API; catches webhooks that
      were missed or failed to process, and reports/repairs the drift. (Also satisfies the
      "≥1 background job" shared requirement in §9 if you pick this one.)
- [ ] **A full test suite** — beyond the four required tests: cover the scary edge cases
      (concurrent duplicate requests, out-of-order webhooks, clock/timezone boundaries on
      billing periods), keep it deterministic (no real network/time dependence), and
      runnable in one command (`uv run pytest`).
