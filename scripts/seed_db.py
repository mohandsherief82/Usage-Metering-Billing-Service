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
from db.session import SessionLocal, engine


def seed_database() -> None:
    db = SessionLocal()
    try:
        print("🌱 Starting database seed...")

        pro_plan = db.query(Plan).filter_by(slug="pro").first()
        if not pro_plan:
            pro_plan = Plan(
                slug="pro",
                name="Pro Tier",
                monthly_api_call_quota=1000,
                monthly_ai_token_quota=100_000,
                price_cents=2900,  # $29.00
                stripe_price_id="price_pro_test_123",
            )
            db.add(pro_plan)
            db.flush()
            print("  Created Plan: Pro Tier")

        enterprise_plan = db.query(Plan).filter_by(slug="enterprise").first()
        if not enterprise_plan:
            enterprise_plan = Plan(
                slug="enterprise",
                name="Enterprise Tier",
                monthly_api_call_quota=50000,
                monthly_ai_token_quota=5_000_000,
                price_cents=19900,  # $199.00
                stripe_price_id="price_ent_test_456",
            )
            db.add(enterprise_plan)
            db.flush()
            print("  Created Plan: Enterprise Tier")

        tenant_acme = db.query(Tenant).filter_by(id="acme").first()
        if not tenant_acme:
            tenant_acme = Tenant(
                id="acme",
                name="Acme Corp",
                stripe_customer_id="cus_acme_123",
                plan_id=pro_plan.id,
                status=TenantStatus.ACTIVE,
            )
            db.add(tenant_acme)
            print("  Created Tenant: acme")

        tenant_globex = db.query(Tenant).filter_by(id="globex").first()
        if not tenant_globex:
            tenant_globex = Tenant(
                id="globex",
                name="Globex Inc",
                stripe_customer_id="cus_globex_456",
                plan_id=pro_plan.id,
                status=TenantStatus.PAST_DUE,
            )
            db.add(tenant_globex)
            print("  Created Tenant: globex")

        db.flush()

        now = datetime.now(timezone.utc)
        sub_acme = db.query(Subscription).filter_by(tenant_id="acme").first()
        if not sub_acme:
            sub_acme = Subscription(
                tenant_id="acme",
                plan_id=pro_plan.id,
                stripe_subscription_id="sub_acme_789",
                status=SubscriptionStatus.ACTIVE,
                current_period_start=now - timedelta(days=15),
                current_period_end=now + timedelta(days=15),
            )
            db.add(sub_acme)
            print("  Created Subscription for: acme")

        usage_exists = db.query(UsageEvent).filter_by(tenant_id="acme").first()
        if not usage_exists:
            sample_events = [
                UsageEvent(
                    tenant_id="acme",
                    event_type=UsageEventType.API_CALL,
                    quantity=1,
                    idempotency_key="seed_event_acme_1",
                    meta={"endpoint": "/v1/chat/completions"},
                ),
                UsageEvent(
                    tenant_id="acme",
                    event_type=UsageEventType.INPUT_TOKENS,
                    quantity=450,
                    idempotency_key="seed_event_acme_2",
                    meta={"model": "gpt-4o"},
                ),
                UsageEvent(
                    tenant_id="acme",
                    event_type=UsageEventType.OUTPUT_TOKENS,
                    quantity=120,
                    idempotency_key="seed_event_acme_3",
                    meta={"model": "gpt-4o"},
                ),
            ]
            db.add_all(sample_events)
            print("  Created Sample Usage Events for: acme")

        db.commit()
        print("✅ Database seeding completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()