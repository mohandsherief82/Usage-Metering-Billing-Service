import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base, Tenant, UsageEvent, UsageEventType


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


def test_tenant_data_isolation(db_session: Session):
    tenant_a = Tenant(id="acme", name="Acme Corp")
    tenant_b = Tenant(id="globex", name="Globex Inc")

    db_session.add_all([tenant_a, tenant_b])
    db_session.commit()

    event_a = UsageEvent(
        tenant_id="acme",
        event_type=UsageEventType.API_CALL,
        quantity=10,
        idempotency_key="key_acme_1",
    )

    event_b = UsageEvent(
        tenant_id="globex",
        event_type=UsageEventType.API_CALL,
        quantity=50,
        idempotency_key="key_globex_1",
    )

    db_session.add_all([event_a, event_b])
    db_session.commit()

    acme_events = db_session.query(UsageEvent).filter_by(tenant_id="acme").all()

    assert len(acme_events) == 1
    assert acme_events[0].tenant_id == "acme"

    assert acme_events[0].quantity == 10

    globex_events = db_session.query(UsageEvent).filter_by(tenant_id="globex").all()

    assert len(globex_events) == 1
    assert globex_events[0].tenant_id == "globex"

    assert globex_events[0].quantity == 50