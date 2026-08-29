import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from db.models import Plan, Subscription, Tenant, UsageEvent
from db.session import SessionLocal


def inspect_db():
    db = SessionLocal()
    try:
        print("=== PLANS ===")
        for plan in db.query(Plan).all():
            print(plan)

        print("\n=== TENANTS ===")
        for tenant in db.query(Tenant).all():
            print(tenant)

        print("\n=== SUBSCRIPTIONS ===")
        for sub in db.query(Subscription).all():
            print(sub)

        print("\n=== USAGE EVENTS ===")
        for event in db.query(UsageEvent).all():
            print(event)

    finally:
        db.close()


if __name__ == "__main__":
    inspect_db()