"""
SQLAlchemy models: Tenant, Plan, Subscription, UsageEvent, WebhookEvent.

Key invariants to enforce here:
- UsageEvent.idempotency_key has a UNIQUE constraint (this IS the
  double-counting guard — see GUIDE.md §3).
- WebhookEvent.id is the Stripe event id itself (PRIMARY KEY) — inserting
  a duplicate id fails fast, which is your webhook replay guard.
- Every tenant-owned row carries tenant_id and every query filters by it —
  no table here should be queryable without a tenant scope in application code.
- Money columns are Integer (cents / micro-units), never Float/Numeric.
"""

# TODO: declarative Base, Tenant, Plan, Subscription, UsageEvent, WebhookEvent
