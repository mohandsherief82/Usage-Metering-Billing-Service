import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from stripe import WebhookSignature

from api.webhooks import webhook_router
from src.config import settings
from db.models import Plan, Subscription, SubscriptionStatus, Tenant, TenantStatus, WebhookEvent
from src.db.session import get_db


@pytest.fixture
def client(db_session):
    app = FastAPI()
    app.include_router(webhook_router)

    app.dependency_overrides[get_db] = lambda: db_session

    return TestClient(app)


@pytest.fixture(autouse=True)
def _fixed_webhook_secret(monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_secret")


def _signed_request(payload: dict):
    payload_str = json.dumps(payload)
    header = WebhookSignature.generate_signature_header(payload_str, "whsec_test_secret")

    return payload_str, {"Stripe-Signature": header, "Content-Type": "application/json"}


def test_valid_signature_is_processed_and_syncs_tenant(client, db_session):
    plan = Plan(
        slug="pro",
        name="Pro",
        monthly_api_call_quota=50_000,
        monthly_ai_token_quota=5_000_000,
        price_cents=2_900,
        stripe_price_id="price_test_pro",
    )
    db_session.add(plan)
    db_session.commit()

    tenant = Tenant(id="acme", name="Acme Corp", status=TenantStatus.ACTIVE, plan_id=None)
    db_session.add(tenant)
    db_session.commit()

    now = int(datetime.now(timezone.utc).timestamp())

    fake_subscription = {
        "id": "sub_test_123",
        "status": "active",
        "current_period_start": now,
        "current_period_end": now + 30 * 24 * 3600,
        "items": {"data": [{"price": {"id": "price_test_pro"}}]},
    }

    payload = {
        "id": "evt_checkout_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_1",
                "client_reference_id": "acme",
                "customer": "cus_test_1",
                "subscription": "sub_test_123",
                "metadata": {"tenant_id": "acme"},
            }
        },
    }

    body, headers = _signed_request(payload)

    with patch("services.stripe_service.stripe.Subscription.retrieve", return_value=fake_subscription):
        response = client.post("/webhooks/stripe", content=body, headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    db_session.refresh(tenant)

    assert tenant.stripe_customer_id == "cus_test_1"
    assert tenant.plan_id == plan.id
    assert tenant.status == TenantStatus.ACTIVE

    subscription = db_session.query(Subscription).filter_by(stripe_subscription_id="sub_test_123").first()

    assert subscription is not None
    assert subscription.status == SubscriptionStatus.ACTIVE

    assert db_session.query(WebhookEvent).filter_by(id="evt_checkout_1").count() == 1


def test_forged_signature_is_rejected_with_400_and_changes_nothing(client, db_session):
    payload = {
        "id": "evt_forged_1",
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_forged", "client_reference_id": "acme"}},
    }

    body = json.dumps(payload)

    response = client.post(
        "/webhooks/stripe",
        content=body,
        headers={
            "Stripe-Signature": "t=12345,v1=not_a_real_signature",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 400
    assert db_session.query(WebhookEvent).count() == 0


def test_missing_signature_header_is_rejected_with_400(client):
    response = client.post(
        "/webhooks/stripe",
        content=json.dumps({"id": "evt_x", "type": "checkout.session.completed"}),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400


def test_replayed_event_is_processed_once(client, db_session):
    tenant = Tenant(id="acme", name="Acme Corp", status=TenantStatus.PAST_DUE, plan_id=None)
    db_session.add(tenant)
    db_session.commit()

    payload = {
        "id": "evt_replay_1",
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_does_not_exist"}},
    }

    body, headers = _signed_request(payload)

    first = client.post("/webhooks/stripe", content=body, headers=headers)
    second = client.post("/webhooks/stripe", content=body, headers=headers)

    assert first.status_code == 200
    assert first.json()["status"] == "success"

    assert second.status_code == 200
    assert second.json()["status"] == "ignored"

    assert db_session.query(WebhookEvent).filter_by(id="evt_replay_1").count() == 1


def test_subscription_updated_syncs_status_and_period(client, db_session):
    plan = Plan(
        slug="pro",
        name="Pro",
        monthly_api_call_quota=50_000,
        monthly_ai_token_quota=5_000_000,
        price_cents=2_900,
    )
    db_session.add(plan)
    db_session.commit()

    tenant = Tenant(id="acme", name="Acme Corp", status=TenantStatus.ACTIVE, plan_id=plan.id)
    db_session.add(tenant)
    db_session.commit()

    now = datetime.now(timezone.utc)

    existing_sub = Subscription(
        tenant_id="acme",
        plan_id=plan.id,
        stripe_subscription_id="sub_update_1",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=30),
        current_period_end=now,
    )
    db_session.add(existing_sub)
    db_session.commit()

    new_period_start = int(now.timestamp())
    new_period_end = int((now + timedelta(days=30)).timestamp())

    payload = {
        "id": "evt_sub_updated_1",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_update_1",
                "status": "past_due",
                "current_period_start": new_period_start,
                "current_period_end": new_period_end,
            }
        },
    }

    body, headers = _signed_request(payload)
    response = client.post("/webhooks/stripe", content=body, headers=headers)

    assert response.status_code == 200

    db_session.refresh(existing_sub)
    db_session.refresh(tenant)

    assert existing_sub.status == SubscriptionStatus.PAST_DUE
    assert tenant.status == TenantStatus.PAST_DUE


def test_subscription_deleted_marks_canceled(client, db_session):
    plan = Plan(
        slug="pro",
        name="Pro",
        monthly_api_call_quota=50_000,
        monthly_ai_token_quota=5_000_000,
        price_cents=2_900,
    )
    db_session.add(plan)
    db_session.commit()

    tenant = Tenant(id="acme", name="Acme Corp", status=TenantStatus.ACTIVE, plan_id=plan.id)
    db_session.add(tenant)
    db_session.commit()

    now = datetime.now(timezone.utc)

    existing_sub = Subscription(
        tenant_id="acme",
        plan_id=plan.id,
        stripe_subscription_id="sub_delete_1",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=10),
        current_period_end=now + timedelta(days=20),
    )
    db_session.add(existing_sub)
    db_session.commit()

    payload = {
        "id": "evt_sub_deleted_1",
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_delete_1"}},
    }

    body, headers = _signed_request(payload)
    response = client.post("/webhooks/stripe", content=body, headers=headers)

    assert response.status_code == 200

    db_session.refresh(existing_sub)
    db_session.refresh(tenant)

    assert existing_sub.status == SubscriptionStatus.CANCELED
    assert tenant.status == TenantStatus.CANCELED
