# Usage Metering & Billing System

Terminal-based usage metering and billing engine for a SaaS company: idempotent
metering, quota enforcement, monthly cost rollups (incl. AI token pricing), and
Stripe subscription billing (test mode) — all inspectable from a Textual TUI.

See **GUIDE.md** for the full build checklist and **architecture.d2** /
**architecture.svg** for the system diagram. Proof-of-correctness transcripts
live in **EVIDENCE.md**.

## Stack

- **Language**: Python 3.11+
- **API**: FastAPI + SQLAlchemy 2.0
- **TUI**: [Textual](https://textual.textualize.io)
- **Payments**: Stripe (test mode only)
- **Build tool**: [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
cp .env.example .env   # fill in Stripe test keys

```

Terminal 1 — API:
```bash
uv run uvicorn main:app --reload

```

Terminal 2 — Stripe webhook forwarding (no tunnel needed):
```bash
stripe listen --forward-to localhost:8000/webhooks/stripe

```

Terminal 3 — TUI dashboard:
```bash
uv run python src/tui/app.py

```

Run tests:
```bash
uv run pytest -v

```

If you want to run everything from a single command and terminal window and you have tmux and the tmuxp uv tool, you can run:
```bash
tmuxp load .

```

Also, you can use the created `Makefile`, to see all available functions in the makefile run:
```bash
make help

```

## Project layout

```
src/
  config.py           pinned pricing constants + settings
  main.py             FastAPI app
  db/                 models, session
  api/                usage / webhooks / checkout routes
  services/            MeterService, QuotaService, CostService, StripeService
  tui/                 Textual app + screens
tests/                 idempotency, quota, cost, webhook tests
scripts/seed_db.py     demo tenants/plans
architecture.d2        system diagram (compile: d2 architecture.d2 architecture.svg)
GUIDE.md               build checklist
EVIDENCE.md            proof of correctness (no double-counting, correct cost totals, webhook security)

```

## API summary

| Route                   | Purpose                                               |
|--------------------------|--------------------------------------------------------|
| `POST /usage/record`    | Record one billable usage event (idempotent)          |
| `GET /usage`            | Rolled-up usage/limit/cost for a tenant                |
| `POST /checkout`        | Create a Stripe Checkout Session (test mode)           |
| `POST /webhooks/stripe` | Stripe webhook receiver (signature-verified, deduped)  |
