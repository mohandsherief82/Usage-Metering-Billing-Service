from src.services.meter_service import MeterService
from src.db.models import UsageEvent, Tenant, Plan


def test_record_usage_idempotency(db_session):
    service = MeterService(db_session)

    event1, is_created1 = service.record(
        tenant_id="acme",
        event_type="input_tokens",
        quantity=100,
        idempotency_key="key_abc_123"
    )

    assert is_created1 is True
    assert event1.idempotency_key == "key_abc_123"

    event2, is_created2 = service.record(
        tenant_id="acme",
        event_type="input_tokens",
        quantity=100,
        idempotency_key="key_abc_123"
    )

    assert is_created2 is False
    assert event2.id == event1.id

    count = db_session.query(UsageEvent).filter_by(idempotency_key="key_abc_123").count()

    assert count == 1