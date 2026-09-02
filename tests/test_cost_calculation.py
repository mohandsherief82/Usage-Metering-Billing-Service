from datetime import datetime, timedelta, timezone

from db.models import Tenant, TenantStatus, UsageEvent, UsageEventType
from services.cost_service import CostService


def test_cost_service_rollup_aggregation(db_session):
    acme = Tenant(id="acme", name="Acme Corp", status=TenantStatus.ACTIVE)
    db_session.add(acme)

    db_session.commit()

    now = datetime.now(timezone.utc)

    start_time = now - timedelta(hours=1)
    end_time = now + timedelta(hours=1)

    e1 = UsageEvent(
        tenant_id="acme",
        event_type=UsageEventType.INPUT_TOKENS,
        quantity=1000,
        idempotency_key="key_1",
        created_at=now,
    )

    e2 = UsageEvent(
        tenant_id="acme",
        event_type=UsageEventType.INPUT_TOKENS,
        quantity=500,
        idempotency_key="key_2",
        created_at=now,
    )

    e3 = UsageEvent(
        tenant_id="acme",
        event_type=UsageEventType.OUTPUT_TOKENS,
        quantity=200,
        idempotency_key="key_3",
        created_at=now,
    )

    e_outside = UsageEvent(
        tenant_id="acme",
        event_type=UsageEventType.INPUT_TOKENS,
        quantity=9999,
        idempotency_key="key_out",
        created_at=now - timedelta(days=2),
    )

    db_session.add_all([e1, e2, e3, e_outside])
    db_session.commit()

    service = CostService(db_session)
    result = service.rollup(tenant_id="acme", start_time=start_time, end_time=end_time)

    assert result["tenant_id"] == "acme"

    breakdown_map = {item["event_type"]: item["quantity"] for item in result["breakdown"]}

    assert breakdown_map["input_tokens"] == 1500  # 1000 + 500
    assert breakdown_map["output_tokens"] == 200

    assert "cached_input_tokens" not in breakdown_map

    # input_tokens: 1500 * 30 = 45,000 microcents
    # output_tokens:  200 * 150 = 30,000 microcents
    # total: 75,000 microcents = 7.5 cents -> 8 (ceiling)
    assert result["total_microcents"] == 75_000
    assert result["total_cents"] == 8
