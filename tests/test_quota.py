import pytest
from fastapi import HTTPException

from db.models import Plan, Tenant, TenantStatus, UsageEvent, UsageEventType
from services.quota_service import QuotaService


def test_quota_under_limit_allowed(db_session):
    plan = Plan(
        id=10,
        slug="pro_under",
        name="Pro Under",
        monthly_api_call_quota=1000,
        monthly_ai_token_quota=100000,
    )

    tenant = Tenant(
        id="acme_under", name="Acme Under", status=TenantStatus.ACTIVE, plan_id=10
    )

    db_session.add_all([plan, tenant])
    db_session.commit()

    for i in range(999):
        db_session.add(
            UsageEvent(
                tenant_id="acme_under",
                event_type=UsageEventType.API_CALL,
                quantity=1,
                idempotency_key=f"key_under_{i}",
            )
        )

    db_session.commit()

    service = QuotaService(db_session)
    service.check_quota("acme_under")


def test_quota_at_limit_rejected_with_429(db_session):
    plan = Plan(
        id=20,
        slug="pro_limit",
        name="Pro Limit",
        monthly_api_call_quota=1000,
        monthly_ai_token_quota=100000,
    )

    tenant = Tenant(
        id="acme_limit", name="Acme Limit", status=TenantStatus.ACTIVE, plan_id=20
    )

    db_session.add_all([plan, tenant])
    db_session.commit()

    for i in range(1001):
        db_session.add(
            UsageEvent(
                tenant_id="acme_limit",
                event_type=UsageEventType.API_CALL,
                quantity=1,
                idempotency_key=f"key_limit_{i}",
            )
        )

    db_session.commit()

    service = QuotaService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.check_quota("acme_limit")

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == {
        "message": "tenant acme_limit is at 1001/1000 API calls for this billing period"
    }


def test_quota_nonexistent_tenant_raises_404(db_session):
    service = QuotaService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.check_quota("nonexistent_tenant")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == {
        "message": "Tenant 'nonexistent_tenant' not found."
    }


def test_quota_past_due_tenant_raises_402(db_session):
    tenant = Tenant(
        id="acme_past_due", name="Acme Past Due", status=TenantStatus.PAST_DUE
    )

    db_session.add(tenant)
    db_session.commit()

    service = QuotaService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.check_quota("acme_past_due")

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail == {
        "message": "Tenant 'acme_past_due' account status is 'past_due'. Payment required."
    }
