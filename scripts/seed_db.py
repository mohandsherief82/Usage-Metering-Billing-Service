import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from db.models import (
    Plan,
    Subscription,
    SubscriptionStatus,
    Tenant,
    TenantStatus,
    UsageEvent,
    UsageEventType,
)
from db.session import SessionLocal

now = datetime.now(timezone.utc)

PLANS = [
    dict(
        slug="free",
        name="Free",
        monthly_api_call_quota=1_000,
        monthly_ai_token_quota=100_000,
        price_cents=0,
        stripe_price_id=None,
    ),
    dict(
        slug="pro",
        name="Pro",
        monthly_api_call_quota=50_000,
        monthly_ai_token_quota=5_000_000,
        price_cents=2_900,
        stripe_price_id="price_test_pro",
    ),
]

TENANTS = [
    dict(id="acme", name="Acme Robotics", plan_slug="pro",
         status=TenantStatus.ACTIVE, stripe_customer_id="cus_acme_123"),
    dict(id="globex", name="Globex Inc", plan_slug="pro",
         status=TenantStatus.PAST_DUE, stripe_customer_id="cus_globex_456"),
    dict(id="initech", name="Initech", plan_slug="free",
         status=TenantStatus.ACTIVE, stripe_customer_id=None),
    dict(id="hooli", name="Hooli", plan_slug="free",
         status=TenantStatus.ACTIVE, stripe_customer_id=None),
    dict(id="stark-industries", name="Stark Industries", plan_slug="pro",
         status=TenantStatus.ACTIVE, stripe_customer_id="cus_stark_789"),
    dict(id="wayne-ent", name="Wayne Enterprises", plan_slug="free",
         status=TenantStatus.ACTIVE, stripe_customer_id="cus_wayne_999"),
]

SUBSCRIPTIONS = {
    "acme": ("sub_acme_001", SubscriptionStatus.ACTIVE, -15, 15),
    "globex": ("sub_globex_001", SubscriptionStatus.PAST_DUE, -20, 10),
    "stark-industries": ("sub_stark_001", SubscriptionStatus.ACTIVE, -5, 25),
    "wayne-ent": ("sub_wayne_001", SubscriptionStatus.CANCELED, -40, -10),
}

USAGE_EVENTS = {
    "acme": [
        (UsageEventType.API_CALL, 1),
        (UsageEventType.API_CALL, 1),
        (UsageEventType.INPUT_TOKENS, 15_000),
        (UsageEventType.CACHED_INPUT_TOKENS, 6_000),
        (UsageEventType.REASONING_TOKENS, 2_200),
        (UsageEventType.OUTPUT_TOKENS, 4_800),
    ],
    "globex": [
        (UsageEventType.API_CALL, 1),
        (UsageEventType.INPUT_TOKENS, 5_000),
        (UsageEventType.OUTPUT_TOKENS, 1_800),
    ],
    "initech": [
        (UsageEventType.API_CALL, 1),
        (UsageEventType.API_CALL, 1),
        (UsageEventType.INPUT_TOKENS, 800),
        (UsageEventType.OUTPUT_TOKENS, 300),
    ],
    "hooli": [
        (UsageEventType.API_CALL, 950),
        (UsageEventType.INPUT_TOKENS, 1_200),
        (UsageEventType.OUTPUT_TOKENS, 400),
    ],
    "stark-industries": [
        (UsageEventType.API_CALL, 1),
        (UsageEventType.INPUT_TOKENS, 22_000),
        (UsageEventType.CACHED_INPUT_TOKENS, 9_000),
        (UsageEventType.OUTPUT_TOKENS, 7_000),
    ],
    "wayne-ent": [],
}


def seed_database() -> None:
    db = SessionLocal()
    try:
        print("Seeding plans...")
        plans_by_slug: dict[str, Plan] = {}

        for p in PLANS:
            plan = db.query(Plan).filter_by(slug=p["slug"]).first()

            if plan is None:
                plan = Plan(**p)
                db.add(plan)

                db.flush()

                print(f"  created plan: {plan.slug}")
            else:
                print(f"  plan already exists: {plan.slug}")

            plans_by_slug[p["slug"]] = plan

        db.commit()

        print("Seeding tenants...")

        for t in TENANTS:
            tenant = db.query(Tenant).filter_by(id=t["id"]).first()

            if tenant is None:
                tenant = Tenant(
                    id=t["id"],
                    name=t["name"],
                    plan_id=plans_by_slug[t["plan_slug"]].id,
                    status=t["status"],
                    stripe_customer_id=t["stripe_customer_id"],
                )

                db.add(tenant)

                print(f"  created tenant: {tenant.id} ({t['plan_slug']}, {t['status'].value})")
            else:
                print(f"  tenant already exists: {tenant.id}")

        db.commit()

        print("Seeding subscriptions...")

        for tenant_id, (stripe_sub_id, status, start_offset, end_offset) in SUBSCRIPTIONS.items():
            existing = db.query(Subscription).filter_by(stripe_subscription_id=stripe_sub_id).first()

            if existing is None:
                tenant = db.query(Tenant).filter_by(id=tenant_id).first()

                sub = Subscription(
                    tenant_id=tenant_id,
                    plan_id=tenant.plan_id,
                    stripe_subscription_id=stripe_sub_id,
                    status=status,
                    current_period_start=now + timedelta(days=start_offset),
                    current_period_end=now + timedelta(days=end_offset),
                )

                db.add(sub)

                print(f"  created subscription: {stripe_sub_id} ({status.value}) for {tenant_id}")
            else:
                print(f"  subscription already exists: {stripe_sub_id}")

        db.commit()

        print("Seeding usage events...")

        created_count = 0

        for tenant_id, events in USAGE_EVENTS.items():
            for i, (event_type, quantity) in enumerate(events, start=1):
                idempotency_key = f"seed-{tenant_id}-{i}"

                existing = db.query(UsageEvent).filter_by(idempotency_key=idempotency_key).first()

                if existing is None:
                    db.add(
                        UsageEvent(
                            tenant_id=tenant_id,
                            event_type=event_type,
                            quantity=quantity,
                            idempotency_key=idempotency_key,
                            meta={"source": "seed_db.py"},
                        )
                    )

                    created_count += 1

        db.commit()

        print(f"  created {created_count} new usage events "
              f"({sum(len(v) for v in USAGE_EVENTS.values())} total defined)")

        print("Done.")
        print(
            f"Summary: {db.query(Plan).count()} plans, "
            f"{db.query(Tenant).count()} tenants, "
            f"{db.query(Subscription).count()} subscriptions, "
            f"{db.query(UsageEvent).count()} usage events."
        )

    except Exception as e:
        db.rollback()

        print(f"Error seeding database: {e}")

        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
